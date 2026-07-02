#!/usr/bin/env python3
"""
s6b — 自动清理 (__free/CLASS/guard) 引用计数 Bug 检测器

与 s6 (smatch 配置) 并行运行，仅依赖 s5 产出的 get/put 函数信息。
检测两类与自动清理宏相关的引用计数 Bug:

  Bug Type 1: __free/CLASS 变量直接 return 给调用者，未使用 no_free_ptr() 转移所有权
              → use-after-free (调用者收到已释放的指针)

  Bug Type 2: 同一函数内手动 put + 自动清理共存
              → double-free (手动释放后，自动清理再次释放)

Usage:
    python s6b_detect_auto_cleanup_bugs.py                          # 完整扫描
    python s6b_detect_auto_cleanup_bugs.py --quick                  # 快速扫描 (仅 Bug1)
    python s6b_detect_auto_cleanup_bugs.py --output /tmp/report.json
    python s6b_detect_auto_cleanup_bugs.py --show-known-bugs        # 验证已知 Bug
"""

import json
import os
import re
import subprocess
import sys
import argparse
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

# 项目内部模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s6b_c_function_parser import (
    extract_function_body,
    find_return_statements,
    function_contains_call,
    find_no_free_ptr_calls,
)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

FUNCTION_RESULT_DIR = os.environ.get(
    "REFCOUNT_FUNCTION_RESULT_DIR",
    os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "FunctionResult", "default")
)
KERNEL_SRC = os.environ.get("REFCOUNT_KERNEL_DIR", "")

# 已知 Bug (用于回归验证)
# 注意：line 是 __free 声明行，实际 return 可能在稍后几行
KNOWN_BUGS = [
    {
        "file": "drivers/power/sequencing/core.c",
        "line": 1011,
        "var": "next",
        "cleanup": "put_device",
        "type": "Bug Type 1: return without no_free_ptr",
    },
    {
        "file": "drivers/pci/tsm.c",
        "line": 668,
        "var": "pf0",
        "cleanup": "pci_dev_put",
        "type": "Bug Type 1: return without no_free_ptr",
    },
]


# ---------------------------------------------------------------------------
# Phase 1: 加载 s5 get/put 函数数据
# ---------------------------------------------------------------------------

def load_s5_function_data(data_dir: str) -> Dict[str, dict]:
    """
    加载 s5 产出的 get/put 函数分类数据。

    Returns:
        {func_name: {purity, functionality_list, type_chain}}
    """
    func_db = {}
    stats = defaultdict(int)

    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            stats['parse_error'] += 1
            continue

        # 跳过列表类型的 JSON
        if isinstance(data, list):
            stats['list_type'] += 1
            continue

        func_name = data.get("function_name", "")
        if not func_name:
            stats['no_name'] += 1
            continue

        # 从 final 或顶层获取 functionality_list
        final = data.get("final", {})
        if isinstance(final, dict) and final.get("status") == "ok":
            fl = final.get("functionality_list", [])
        elif isinstance(final, list):
            fl = data.get("functionality_list", [])
        else:
            fl = data.get("functionality_list", [])

        if not fl:
            stats['empty_fl'] += 1
            continue

        # 提取 get/put 信息
        ops = []
        type_chains = []
        for item in fl:
            if len(item) >= 5:
                ops.append(item[0])          # "get" / "put"
                type_chains.append(item[4])  # "device--kobject--kref--refcount_t"

        func_db[func_name] = {
            "purity": data.get("purity", "unknown"),
            "operations": ops,
            "type_chains": type_chains,
            "functionality_list": fl,
        }
        stats['loaded'] += 1

    print(f"[Phase 1] 加载 s5 数据: {stats['loaded']} 个函数 "
          f"(跳过 {stats['empty_fl']} 个空 functionality_list, "
          f"{stats['parse_error']} 个解析错误)")
    return func_db


# ---------------------------------------------------------------------------
# Phase 2: 扫描内核源码 — 提取自动清理定义
# ---------------------------------------------------------------------------

def extract_cleanup_defs(kernel_dir: str) -> List[dict]:
    """
    提取 DEFINE_FREE / DEFINE_CLASS / DEFINE_GUARD 宏定义。

    Returns:
        [{macro, name, type, put_function, get_function?, file, line}]
    """
    results = []

    # DEFINE_FREE(name, type, free_expr)
    cmd = (
        f"grep -rn --include='*.h' --include='*.c' "
        f"-E 'DEFINE_FREE\\([a-zA-Z_]+,' {kernel_dir} "
        f"2>/dev/null | grep -v '\\*/\|//\\|Binary'"
    )
    try:
        raw = subprocess.run(cmd, shell=True, capture_output=True,
                             text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        raw = ""

    for line in raw.strip().split('\n'):
        if not line.strip():
            continue
        # 格式: file:line:code
        parts = line.split(':', 2)
        if len(parts) < 3:
            continue
        file_path, line_no = parts[0], parts[1]
        code = parts[2].strip()

        # 提取宏参数: DEFINE_FREE(name, type, free)
        # 需要处理嵌套括号
        m = _parse_macro_args(code, 'DEFINE_FREE')
        if m and len(m) >= 3:
            name = m[0].strip()
            typ = m[1].strip()
            free_expr = ','.join(m[2:]).strip()
            put_fn = _extract_function_call(free_expr)
            results.append({
                "macro": "DEFINE_FREE",
                "name": name,
                "type": typ,
                "free_expr": free_expr,
                "put_function": put_fn,
                "file": file_path,
                "line": int(line_no),
            })

    # DEFINE_CLASS(name, type, exit, init, init_args...)
    cmd2 = (
        f"grep -rn --include='*.h' --include='*.c' "
        f"-E 'DEFINE_CLASS\\([a-zA-Z_]+,' {kernel_dir} "
        f"2>/dev/null | grep -v '\\*/\|//\|Binary'"
    )
    try:
        raw2 = subprocess.run(cmd2, shell=True, capture_output=True,
                              text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        raw2 = ""

    for line in raw2.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(':', 2)
        if len(parts) < 3:
            continue
        file_path, line_no = parts[0], parts[1]
        code = parts[2].strip()

        m = _parse_macro_args(code, 'DEFINE_CLASS')
        if m and len(m) >= 4:
            name = m[0].strip()
            typ = m[1].strip()
            exit_expr = m[2].strip()
            init_expr = m[3].strip()
            put_fn = _extract_function_call(exit_expr)
            get_fn = _extract_function_call(init_expr)
            results.append({
                "macro": "DEFINE_CLASS",
                "name": name,
                "type": typ,
                "exit_expr": exit_expr,
                "init_expr": init_expr,
                "put_function": put_fn,
                "get_function": get_fn,
                "file": file_path,
                "line": int(line_no),
            })

    print(f"[Phase 2] 提取自动清理定义: {len(results)} 个 "
          f"(DEFINE_FREE: {sum(1 for r in results if r['macro']=='DEFINE_FREE')}, "
          f"DEFINE_CLASS: {sum(1 for r in results if r['macro']=='DEFINE_CLASS')})")
    return results


# ---------------------------------------------------------------------------
# Phase 2b: 提取 __free / CLASS / guard 变量声明
# ---------------------------------------------------------------------------

def extract_auto_vars(kernel_dir: str) -> List[dict]:
    """提取 __free(name) / CLASS(name, var) 变量声明。"""
    results = []

    # __free(name) 声明
    cmd = (
        f"grep -rn --include='*.c' "
        f"-E '__free\\([a-zA-Z_][a-zA-Z_0-9]*\\)' {kernel_dir} "
        f"2>/dev/null | grep -v 'Binary'"
    )
    try:
        raw = subprocess.run(cmd, shell=True, capture_output=True,
                             text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        raw = ""

    # 匹配: 变量名紧邻 __free(cleanup_name)
    # (?<!\w) 确保 __free 不是函数名的一部分 (如 btf__free 是函数名不是宏)
    # 仅匹配最接近 __free( 的那个 \w+，避免逗号声明中的误匹配
    free_pattern = re.compile(
        r'\b(\w+)\s*(?<!\w)__free\((\w+)\)'   # var_name + cleanup_name
    )

    for line in raw.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(':', 2)
        if len(parts) < 3:
            continue
        file_path, line_no_str, code = parts[0], parts[1], parts[2].strip()

        m = free_pattern.search(code)
        if m:
            var_name = m.group(1).strip()
            cleanup_name = m.group(2).strip()
            var_type = ""  # simplified: no longer extracting full type

            # 尝试提取初始化表达式
            init_expr = ""
            eq_pos = code.find('=', m.end())
            if eq_pos >= 0:
                init_part = code[eq_pos + 1:].strip()
                # 截断到 ; 或行尾
                semi = init_part.find(';')
                init_expr = init_part[:semi].strip() if semi >= 0 else init_part

            results.append({
                "mechanism": "__free",
                "cleanup_name": cleanup_name,
                "var_name": var_name,
                "var_type": var_type,
                "init_expr": init_expr,
                "file": file_path,
                "line": int(line_no_str),
            })

    # CLASS(name, var)(args) 声明
    class_pattern = re.compile(
        r'CLASS\(([a-zA-Z_][a-zA-Z_0-9]*),\s*([a-zA-Z_][a-zA-Z_0-9]*)\)'
    )
    cmd2 = (
        f"grep -rn --include='*.c' "
        f"-E 'CLASS\\([a-zA-Z_]+,\\s*[a-zA-Z_]+\\).*\\(' {kernel_dir} "
        f"2>/dev/null | grep -v 'Binary\|DEFINE_CLASS'"
    )
    try:
        raw2 = subprocess.run(cmd2, shell=True, capture_output=True,
                              text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        raw2 = ""

    for line in raw2.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(':', 2)
        if len(parts) < 3:
            continue
        file_path, line_no_str, code = parts[0], parts[1], parts[2].strip()

        m = class_pattern.search(code)
        if m:
            class_name = m.group(1)
            var_name = m.group(2)

            # 提取参数
            args = ""
            args_match = re.search(r'\)\s*\(([^)]*)\)', code[m.end():])
            if args_match:
                # 加回去前面部分的长度
                args = args_match.group(1)

            results.append({
                "mechanism": "CLASS",
                "class_name": class_name,
                "var_name": var_name,
                "init_args": args,
                "file": file_path,
                "line": int(line_no_str),
            })

    print(f"[Phase 2b] 提取自动变量声明: {len(results)} 个 "
          f"(__free: {sum(1 for r in results if r['mechanism']=='__free')}, "
          f"CLASS: {sum(1 for r in results if r['mechanism']=='CLASS')})")
    return results


# ---------------------------------------------------------------------------
# Phase 3: Bug Type 1 — return without no_free_ptr
# ---------------------------------------------------------------------------

def detect_bug_type1(auto_vars: List[dict],
                      cleanup_defs: List[dict]) -> List[dict]:
    """
    检测: __free/CLASS 变量直接 return，未使用 no_free_ptr()。

    算法:
      1. 找到 __free var 所在的函数体
      2. 检查所有 return 语句
      3. 若 var 被 return，检查是否使用了 no_free_ptr(var)
    """
    bugs = []
    cleanup_map = {c['name']: c for c in cleanup_defs}

    for av in auto_vars:
        if av['mechanism'] != '__free':
            # CLASS 的变量名是局部不可见的，暂不追踪
            continue

        file_path = os.path.join(KERNEL_SRC, av['file'])
        if not os.path.exists(file_path):
            file_path = av['file']  # 可能已经是绝对路径

        var_name = av['var_name']

        # 找到变量所在的函数名
        func_name = _find_enclosing_function(file_path, av['line'],
                                              av.get('init_expr', ''))

        if not func_name:
            continue

        # 提取函数体
        # 提取函数体 (从变量声明行向前搜索函数定义)
        func_body = extract_function_body(file_path, func_name, av['line'])
        if not func_body:
            continue

        # 检查 return 语句 — 只匹配 return var; (不含 -> 或 . 字段访问)
        return_stmts = find_return_statements(func_body)
        has_return_var = any(
            re.search(rf'^\s*{re.escape(var_name)}\s*$', expr.strip())
            for expr, _ in return_stmts
        )

        if not has_return_var:
            continue

        # 检查是否为 ERR_PTR 返回路径 (如 ret < 0 时 return ERR_PTR)
        # 此时清理函数通常有 IS_ERR_OR_NULL 保护，不会实际释放
        if _is_err_ptr_return(func_body, var_name):
            continue

        # 检查 no_free_ptr / return_ptr
        has_transfer = find_no_free_ptr_calls(func_body, var_name)

        if not has_transfer:
            cleanup_info = cleanup_map.get(av['cleanup_name'], {})
            put_fn = cleanup_info.get('put_function', av['cleanup_name'])

            bugs.append({
                "bug_type": "Bug Type 1: return without no_free_ptr()",
                "severity": "HIGH",
                "file": av['file'],
                "line": av['line'],
                "var_name": var_name,
                "cleanup_name": av['cleanup_name'],
                "put_function": put_fn,
                "function": func_name,
                "description": (
                    f"变量 '{var_name}' (__free({av['cleanup_name']})) "
                    f"在函数 '{func_name}' 中被 return，"
                    f"但未使用 no_free_ptr() 转移所有权。"
                    f"自动清理将调用 {put_fn}() 释放引用，"
                    f"调用者收到悬空指针。"
                ),
                "fix": f"将 'return {var_name};' 改为 'return no_free_ptr({var_name});' "
                       f"或 'return_ptr({var_name});'",
            })

    print(f"[Phase 3] Bug Type 1 检测: 发现 {len(bugs)} 个")
    return bugs


# ---------------------------------------------------------------------------
# Phase 4: Bug Type 2 — 手动 put + 自动清理
# ---------------------------------------------------------------------------

def detect_bug_type2(auto_vars: List[dict],
                      cleanup_defs: List[dict],
                      func_db: Dict[str, dict]) -> List[dict]:
    """
    检测: 手动 put + 自动清理在同函数中共存 (可能 double-free)。

    算法:
      1. 解析 __free(cleanup_name) → put_function
      2. 在同函数中搜索手动调用 put_function(var_name)
      3. 若存在且 no_free_ptr(var) 不在手动 put 之前 → warning
    """
    bugs = []
    cleanup_map = {}
    for c in cleanup_defs:
        if c.get('put_function'):
            cleanup_map[c['name']] = c['put_function']
        # 对于 DEFINE_CLASS，name 本身可能被设为 cleanup_name
        if c['macro'] == 'DEFINE_CLASS' and c.get('put_function'):
            cleanup_map[c['name']] = c['put_function']

    for av in auto_vars:
        if av['mechanism'] != '__free':
            continue

        cleanup_name = av['cleanup_name']
        put_fn = cleanup_map.get(cleanup_name, cleanup_name)

        file_path = os.path.join(KERNEL_SRC, av['file'])
        if not os.path.exists(file_path):
            file_path = av['file']

        var_name = av['var_name']
        func_name = _find_enclosing_function(file_path, av['line'],
                                              av.get('init_expr', ''))
        if not func_name:
            continue

        func_body = extract_function_body(file_path, func_name, av['line'])
        if not func_body:
            continue

        # 搜索手动调用 put_fn
        manual_put_lines = function_contains_call(func_body, put_fn, var_name)
        if not manual_put_lines:
            # 也尝试搜索其他已知的 put 函数 (从 func_db 中匹配)
            continue

        # 检查 no_free_ptr 是否出现在所有手动 put 之前
        has_transfer = find_no_free_ptr_calls(func_body, var_name)
        body_lines = func_body.split('\n')

        # 对于每个手动 put，判断风险
        for put_line in manual_put_lines:
            # 检查手动 put 后紧跟重新赋值 (cdat.c 模式)
            # 如: free_perf_xa(usp_xa); usp_xa = working_xa;
            # 此时手动 put 释放旧值，__free 管理新值 — 正确
            if _is_reassigned_after(body_lines, put_line, var_name):
                continue

            # 检查 no_free_ptr 是否在手动 put 之前出现
            # 如已转移所有权，__free 被抑制 — 安全
            if has_transfer and _no_free_before_line(func_body, var_name, put_line):
                continue
            if has_transfer:
                # 可能已经转移了所有权 (但需要路径确认)
                bugs.append({
                    "bug_type": "Bug Type 2: manual put + auto cleanup (needs path review)",
                    "severity": "WARNING",
                    "file": av['file'],
                    "line": av['line'] + put_line - 1,
                    "var_name": var_name,
                    "cleanup_name": cleanup_name,
                    "put_function": put_fn,
                    "function": func_name,
                    "description": (
                        f"变量 '{var_name}' (__free({cleanup_name})) "
                        f"在函数 '{func_name}' 中同时被手动 {put_fn}() "
                        f"和自动清理释放。存在 no_free_ptr() 转移，"
                        f"但需人工确认路径是否互斥。"
                    ),
                })
            else:
                bugs.append({
                    "bug_type": "Bug Type 2: manual put + auto cleanup",
                    "severity": "HIGH",
                    "file": av['file'],
                    "line": av['line'] + put_line - 1,
                    "var_name": var_name,
                    "cleanup_name": cleanup_name,
                    "put_function": put_fn,
                    "function": func_name,
                    "description": (
                        f"变量 '{var_name}' (__free({cleanup_name})) "
                        f"在函数 '{func_name}' 中同时被手动 {put_fn}() "
                        f"(第 {put_line} 行) 和自动清理释放。"
                        f"如果两者在同一条代码路径上执行，"
                        f"将导致 double-free。"
                        f"建议: 使用 no_free_ptr({var_name}) 后手动 put，"
                        f"或移除手动 put 完全依赖自动清理。"
                    ),
                })

    print(f"[Phase 4] Bug Type 2 检测: 发现 {len(bugs)} 个 warning")
    return bugs


# ---------------------------------------------------------------------------
# Phase 5: Cross-Validation
# ---------------------------------------------------------------------------

def cross_validate(auto_vars: List[dict],
                    cleanup_defs: List[dict],
                    func_db: Dict[str, dict]) -> List[dict]:
    """
    用 s5 的 get/put 函数数据做交叉验证。

    检查:
      1. __free(cleanup) 的 put_function 是否在 s5 中被识别为 "put"
      2. 初始化表达式中的 get 函数是否与 put 函数类型匹配
    """
    issues = []
    cleanup_map = {}
    for c in cleanup_defs:
        if c.get('put_function'):
            cleanup_map[c['name']] = c

    for av in auto_vars:
        if av['mechanism'] != '__free':
            continue

        cleanup_name = av['cleanup_name']
        cleanup_info = cleanup_map.get(cleanup_name, {})
        put_fn = cleanup_info.get('put_function', cleanup_name)

        # 检查 put_fn 是否在 s5 数据库中被识别为 get 而非 put
        if put_fn in func_db:
            ops = func_db[put_fn].get('operations', [])
            if 'get' in ops and 'put' not in ops:
                issues.append({
                    "type": "cross_validation",
                    "severity": "INFO",
                    "file": av['file'],
                    "line": av['line'],
                    "description": (
                        f"__free({cleanup_name}) 的 put_function '{put_fn}' "
                        f"在 s5 数据中被标记为 'get' 而非 'put'，"
                        f"请确认清理函数是否正确。"
                    ),
                })

    print(f"[Phase 5] Cross-Validation: 发现 {len(issues)} 个问题")
    return issues


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _parse_macro_args(code: str, macro_name: str) -> Optional[List[str]]:
    """解析 DEFINE_FREE(name, type, free) 等宏的参数 (处理嵌套括号)。"""
    # 找到 macro_name( 的位置
    start = code.find(macro_name + '(')
    if start < 0:
        return None

    paren_start = start + len(macro_name) + 1
    depth = 0
    args = []
    current = []
    i = paren_start
    while i < len(code):
        ch = code[i]
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            if depth == 0:
                # 宏的闭合括号
                args.append(''.join(current).strip())
                break
            else:
                depth -= 1
                current.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1

    return args if args else None


def _is_reassigned_after(body_lines: list, put_line: int, var_name: str) -> bool:
    """检查手动 put 后 2 行内是否紧跟重新赋值 (如 usp_xa = working_xa)。"""
    for i in range(put_line, min(put_line + 3, len(body_lines))):
        if re.search(rf'\b{re.escape(var_name)}\s*=\s*', body_lines[i]):
            return True
    return False


def _no_free_before_line(func_body: str, var_name: str,
                          put_line: int) -> bool:
    """检查 no_free_ptr(var) 是否在手动 put 之前出现。"""
    nf_match = re.search(rf'no_free_ptr\({re.escape(var_name)}\)', func_body)
    if not nf_match:
        return False
    nf_line = func_body[:nf_match.start()].count('\n') + 1
    return nf_line < put_line


def _extract_function_call(expr: str) -> Optional[str]:
    """
    从 DEFINE_FREE/DEFINE_CLASS 的表达式中提取实际的清理函数名。

    策略: 找到所有 func(_T) 调用，返回最后一个（通常第一个是条件检查如
    IS_ERR_OR_NULL(_T)，最后一个才是实际的清理函数如 kfree(_T)）。

    'if (!IS_ERR_OR_NULL(_T)) kfree(_T)' → 'kfree'
    'if (_T) put_device(_T)' → 'put_device'
    'fdput(_T)' → 'fdput'
    """
    matches = re.findall(r'(\w+)\s*\(\s*(?:&\s*)?_T\b', expr)
    if matches:
        return matches[-1]  # 返回最后一个匹配（实际的清理函数）
    # 回退: 匹配任何 func( 模式
    m = re.search(r'(\w+)\s*\(', expr)
    return m.group(1) if m else None


def _is_err_ptr_return(func_body: str, var_name: str) -> bool:
    """
    检查 return var; 是否仅在 var 为 ERR_PTR 的路径上执行。

    模式:
      ret = PTR_ERR_OR_ZERO(var);
      if (ret == -ENOENT) return ERR_PTR(-ENOENT);
      else if (ret < 0) return var;   ← var 是 ERR_PTR, kfree 有 IS_ERR_OR_NULL 保护

    启发式: 搜索 return var; 前面的 5 行是否包含 PTR_ERR_OR_ZERO 或 IS_ERR 检查。
    """
    lines = func_body.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 找到 return var; 的位置
        if re.match(rf'return\s+{re.escape(var_name)}\s*;\s*$', stripped):
            # 向前搜索 5 行，检查是否有 ERR_PTR 相关判断
            context = '\n'.join(lines[max(0, i - 5):i])
            if re.search(r'PTR_ERR_OR_ZERO\s*\(\s*' + re.escape(var_name), context):
                return True
            if re.search(r'IS_ERR_OR_NULL\s*\(\s*' + re.escape(var_name), context):
                return True
            if re.search(r'if\s*\(.*ret\s*[<>]', context) and \
               re.search(r'ERR_PTR', context):
                return True
    return False


def _find_enclosing_function(file_path: str, line_no: int,
                               init_expr: str = "") -> Optional[str]:
    """
    根据行号找到包含该行的函数名。

    策略:
      1. 从 line_no 向前搜索函数定义候选
      2. 验证 line_no 在候选函数的 { } 范围内
      3. 支持单行和多行函数签名
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except (IOError, OSError):
        return None

    ctrl_keywords = {'if', 'for', 'while', 'switch', 'return'}

    # 第一步: 收集所有函数定义候选 (行号 → 函数名)
    candidates = {}  # {def_line: (func_name, brace_start_line)}
    for i in range(max(0, line_no - 200), min(len(lines), line_no + 1)):
        line = lines[i].strip()
        if not line or line.startswith('/*') or line.startswith('*') or \
           line.startswith('//') or line.startswith('#'):
            continue
        first_word = line.split()[0] if line.split() else ''
        if first_word in ctrl_keywords or line == '{':
            continue

        # 单行签名
        m = re.search(r'(\w+)\s*\([^)]*\)\s*$', line)
        if m and m.group(1) not in ctrl_keywords:
            if i + 1 < len(lines) and '{' in lines[i + 1]:
                candidates[i] = (m.group(1), i + 1)
            elif '{' in lines[i]:
                paren_end = line.rfind(')')
                brace_pos = line.find('{')
                if brace_pos > paren_end:
                    candidates[i] = (m.group(1), i)
        # 多行签名
        elif re.search(r'\)\s*$', line) and not re.search(r'\w+\s*\(', line):
            if i > 0:
                prev = lines[i - 1].strip()
                pm = re.search(r'(\w+)\s*\(', prev)
                if pm and pm.group(1) not in ctrl_keywords:
                    if i + 1 < len(lines) and '{' in lines[i + 1]:
                        candidates[i - 1] = (pm.group(1), i + 1)

    # 第二步: 验证 target_line 是否在函数大括号内
    for def_line in sorted(candidates.keys(), reverse=True):
        func_name, brace_line = candidates[def_line]
        if brace_line >= line_no:
            continue  # 函数在 target 之后才开始
        # 追踪到闭合大括号
        depth = 0
        for j in range(brace_line, len(lines)):
            for ch in lines[j]:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        if j >= line_no:
                            return func_name  # target 在函数范围内
                        break
            if depth == 0:
                break  # 函数已结束, target 不在范围内

    return None


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="s6b — 自动清理 (__free/CLASS/guard) 引用计数 Bug 检测器")
    parser.add_argument("--quick", action="store_true",
                        help="快速扫描 (仅 Bug Type 1)")
    parser.add_argument("--output", type=str, default=None,
                        help="输出 JSON 报告路径")
    parser.add_argument("--show-known-bugs", action="store_true",
                        help="显示已知 Bug 验证结果")
    parser.add_argument("--data-dir", type=str,
                        default=FUNCTION_RESULT_DIR,
                        help="s5 FunctionResult 目录")
    parser.add_argument("--kernel-dir", type=str,
                        default=KERNEL_SRC,
                        help="Linux 内核源码目录")
    args = parser.parse_args()

    # Phase 1
    func_db = load_s5_function_data(args.data_dir)

    # Phase 2
    cleanup_defs = extract_cleanup_defs(args.kernel_dir)
    auto_vars = extract_auto_vars(args.kernel_dir)

    # Phase 3
    bugs_t1 = detect_bug_type1(auto_vars, cleanup_defs)

    # Phase 4 (skip in quick mode)
    bugs_t2 = []
    if not args.quick:
        bugs_t2 = detect_bug_type2(auto_vars, cleanup_defs, func_db)

    # Phase 5
    issues = cross_validate(auto_vars, cleanup_defs, func_db)

    all_bugs = bugs_t1 + bugs_t2 + issues

    # ── 输出 ──
    print("\n" + "=" * 70)
    print(f"s6b 检测完成: {len(bugs_t1)} 个 Bug Type 1, "
          f"{len(bugs_t2)} 个 Bug Type 2, "
          f"{len(issues)} 个 cross-validation 问题")
    print("=" * 70)

    if all_bugs:
        _print_report(all_bugs)

    # 验证已知 Bug
    if args.show_known_bugs:
        _verify_known_bugs(bugs_t1 + bugs_t2)

    # 保存报告
    if args.output:
        report = {
            "summary": {
                "bug_type1_count": len(bugs_t1),
                "bug_type2_count": len(bugs_t2),
                "cross_validation_issues": len(issues),
                "total_auto_vars": len(auto_vars),
                "total_cleanup_defs": len(cleanup_defs),
            },
            "bugs": all_bugs,
        }
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存至: {args.output}")

    return 0 if not bugs_t1 else 1


def _print_report(bugs: List[dict]):
    """以可读格式输出 Bug 报告。"""
    print("\n" + "-" * 70)
    for i, bug in enumerate(bugs, 1):
        severity_marker = "🔴" if bug.get('severity') == 'HIGH' else \
                          "🟡" if bug.get('severity') == 'WARNING' else "ℹ️"
        print(f"\n{severity_marker} [{bug['bug_type']}]")
        print(f"   文件: {bug['file']}:{bug['line']}")
        if bug.get('function'):
            print(f"   函数: {bug['function']}()")
        if bug.get('var_name'):
            print(f"   变量: {bug['var_name']}")
        if bug.get('put_function'):
            print(f"   涉及: {bug['put_function']}()")
        print(f"   描述: {bug['description']}")
        if bug.get('fix'):
            print(f"   修复: {bug['fix']}")
    print()


def _verify_known_bugs(found_bugs: List[dict]):
    """验证已知 Bug 是否被检出。"""
    print("\n" + "-" * 70)
    print("已知 Bug 验证:")
    def _rel_path(path: str) -> str:
        """从绝对路径中提取相对于内核源码树的部分。"""
        parts = path.split('/')
        for i, p in enumerate(parts):
            if p.startswith('linux-'):
                return '/'.join(parts[i + 1:])
        return path

    found_files = {(_rel_path(b['file']), b.get('line', 0)) for b in found_bugs}

    for kb in KNOWN_BUGS:
        key = (kb['file'], kb['line'])
        status = "✅ 已检出" if key in found_files else "❌ 漏检"
        print(f"  {status} — {kb['file']}:{kb['line']} ({kb['var']}) [{kb['type']}]")
    print()


if __name__ == "__main__":
    sys.exit(main())
