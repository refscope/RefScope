#!/usr/bin/env python3
"""
btf_chain_enumerator.py — 分析线 1: BTF 暴力枚举

从 caller 参数/返回值的 struct 类型出发，枚举所有能到达 atomic_t
的字段路径，过滤出匹配 callee type_chain 的候选链。

不依赖函数体分析，只依赖 BTF 类型信息。

用法:
    python3 btf_chain_enumerator.py --type kobject --callee-chain "kref--refcount_struct--atomic_t"
"""

import re
import subprocess
import json
import sys
import os
from typing import Dict, List, Optional, Set, Tuple
from collections import deque, defaultdict

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BPFTOOL = os.environ.get("REFCOUNT_BPFTOOL", "bpftool")
# BTF_PATH = "/sys/kernel/btf/vmlinux"  # 运行内核 BTF (5.15)
BTF_PATH = os.environ.get("REFCOUNT_BTF_PATH", "/sys/kernel/btf/vmlinux")
PAHOLE_VMLINUX = os.environ.get("REFCOUNT_VMLINUX", "")
MAX_DEPTH = 4
TARGET_TERMINAL = "atomic_t"


# ---------------------------------------------------------------------------
# BTF 类型图构建
# ---------------------------------------------------------------------------

def _load_btf_c_dump(btf_path: str = BTF_PATH) -> str:
    """调用 bpftool 获取 BTF C 格式 dump（缓存）。"""
    if not hasattr(_load_btf_c_dump, '_cache'):
        try:
            result = subprocess.run(
                [BPFTOOL, "btf", "dump", "file", btf_path, "format", "c"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                _load_btf_c_dump._cache = result.stdout
            else:
                _load_btf_c_dump._cache = ""
        except Exception as e:
            print(f"Warning: bpftool failed: {e}", file=sys.stderr)
            _load_btf_c_dump._cache = ""
    return _load_btf_c_dump._cache


def _parse_struct_def(dump: str, struct_name: str) -> Optional[str]:
    """从 BTF C dump 中提取指定 struct 的完整定义文本。"""
    pattern = rf'^struct {re.escape(struct_name)}\s*\{{'
    lines = dump.split('\n')
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip()):
            body = [line]
            depth = line.count('{') - line.count('}')
            for j in range(i + 1, len(lines)):
                body.append(lines[j])
                depth += lines[j].count('{') - lines[j].count('}')
                if depth <= 0:
                    break
            return '\n'.join(body)
    return None


def _strip_type_keywords(type_str: str) -> str:
    """去掉 C 关键字前缀和指针标记，返回裸类型名。"""
    t = type_str.strip().replace('*', '').strip()
    for kw in ['struct ', 'enum ', 'union ', 'const ', 'volatile ', 'unsigned ', 'signed ']:
        t = t.replace(kw, '')
    # 处理 "unsigned int" / "long unsigned int" 等多词类型
    t = t.strip()
    if ' ' in t:
        # 多词基础类型，不可作为 struct 遍历
        return t.replace(' ', '_')
    return t


def _parse_struct_fields(struct_def_text: str) -> List[Tuple[str, str]]:
    """
    从 struct 定义文本中解析字段列表。

    返回: [(field_name, field_type), ...]
      field_type 是去掉 struct/enum/union 前缀的裸类型名（如 "kref", "atomic_t"）

    处理：
      - 跳过匿名 union/struct 的内部字段（把它们提升到父级）
      - 跳过位域
      - 跳过函数指针
    """
    fields = []
    lines = struct_def_text.split('\n')

    # 去掉首行 "struct foo {" 和末行 "};"
    inner_lines = []
    in_body = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('struct ') and '{' in stripped:
            in_body = True
            continue
        if stripped == '};':
            break
        if not in_body:
            continue
        inner_lines.append(line)

    # 解析每个字段声明
    # 字段格式：type field_name; 或 type field_name: N; (位域)
    # 需要跳过嵌套的 { } 块（匿名 union/struct）
    full_text = '\n'.join(inner_lines)

    # 简化策略：逐行解析，跳过含 { 的行
    for line in inner_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue
        if '{' in stripped or '}' in stripped:
            continue  # 跳过匿名 union/struct 的开闭括号

        # 匹配: type_name field_name;
        # 或:   type_name field_name[expr];
        m = re.match(r'^(.+?)\s+(\w+)\s*(?:\[.*\])?\s*;', stripped)
        if m:
            type_str = m.group(1).strip()
            field_name = m.group(2).strip()
            bare_type = _strip_type_keywords(type_str)
            if bare_type:
                fields.append((field_name, bare_type))
            continue

        # 位域: type_name field_name : N;
        m = re.match(r'^(.+?)\s+(\w+)\s*:\s*\d+\s*;', stripped)
        if m:
            type_str = m.group(1).strip()
            field_name = m.group(2).strip()
            bare_type = _strip_type_keywords(type_str)
            if bare_type:
                fields.append((field_name, bare_type))

    return fields


def _get_typedef_target(dump: str, type_name: str) -> Optional[str]:
    """查询 typedef 的实际类型（如 refcount_t → refcount_struct）。"""
    pattern = rf'^typedef\s+.*\s+{re.escape(type_name)}\s*;'
    for line in dump.split('\n'):
        if re.match(pattern, line.strip()):
            parts = line.strip().rstrip(';').split()
            # "typedef struct refcount_struct refcount_t"
            # 找 typedef 和 type_name 之间的类型
            idx = -1
            for k, p in enumerate(parts):
                if p == type_name:
                    idx = k
                    break
            if idx >= 2:
                underlying = ' '.join(parts[1:idx])
                bare = _strip_type_keywords(underlying)
                if bare:
                    return bare
    return None


# ---------------------------------------------------------------------------
# 类型图缓存
# ---------------------------------------------------------------------------

_type_graph: Dict[str, List[Tuple[str, str]]] = {}  # struct_name → [(field_name, field_type), ...]
_typedef_map: Dict[str, str] = {}                    # typedef → underlying type
_reachability: Dict[str, Set[str]] = {}              # struct_name → set of reachable types


def _load_pahole_dump() -> str:
    """调用 pahole 获取所有 struct 的完整 DWARF 定义（缓存，约88K struct）。"""
    if not hasattr(_load_pahole_dump, '_cache'):
        try:
            result = subprocess.run(
                ["pahole", PAHOLE_VMLINUX],
                capture_output=True, text=True, timeout=300
            )
            _load_pahole_dump._cache = result.stdout if result.returncode == 0 else ""
        except Exception:
            _load_pahole_dump._cache = ""
    return _load_pahole_dump._cache


def _remove_attribute(text: str) -> str:
    """移除 __attribute__((...)) 块（处理嵌套括号）。"""
    while '__attribute__' in text:
        idx = text.index('__attribute__')
        paren_start = text.index('((', idx)
        depth = 2
        pos = paren_start + 2
        while depth > 0 and pos < len(text):
            if text[pos:pos+2] == '((':
                depth += 2; pos += 2
            elif text[pos:pos+2] == '))':
                depth -= 2; pos += 2
            elif text[pos] == '(':
                depth += 1; pos += 1
            elif text[pos] == ')':
                depth -= 1; pos += 1
            else:
                pos += 1
        text = text[:idx] + text[pos:]
    return text


def _parse_pahole_fields(struct_def_text: str) -> List[Tuple[str, str]]:
    """
    从 pahole 输出中解析字段列表（状态机，处理嵌套 union/struct）。

    策略: 逐行扫描，跟踪 brace depth。对于以 ; 结尾的行，
    提取最后一个 ; 之前的 type 和 field name。

    返回: [(field_name, bare_type), ...]
    """
    fields = []
    lines = struct_def_text.split('\n')
    brace_depth = 0
    started = False

    for line in lines:
        stripped = line.strip()
        if not started:
            if 'struct ' in stripped and '{' in stripped:
                started = True
                brace_depth = stripped.count('{') - stripped.count('}')
            continue

        if not stripped:
            continue

        # 更新 brace depth
        brace_depth += stripped.count('{') - stripped.count('}')
        if brace_depth <= 0:
            break

        # 跳过纯注释和分隔线
        if stripped.startswith('/*') and ('cacheline' in stripped or 'size:' in stripped or 'XXX' in stripped or '---' in stripped):
            continue

        # 跳过只含 { 或 } 的行
        if stripped in ('{', '}', '};'):
            continue
        if re.match(r'^(struct|union|enum)\s+\w*\s*\{', stripped):
            continue

        # 移除以 /* 开头的行尾注释
        comment_idx = stripped.find('/*')
        if comment_idx >= 0:
            stripped = stripped[:comment_idx].strip()

        # 移除 __attribute__((...))
        stripped = _remove_attribute(stripped)

        if not stripped.endswith(';'):
            continue

        # 现在 stripped 是 "type name;" 或 "type name:N;" 的形式
        stripped = stripped.rstrip(';').strip()

        # 分离 type 和 field name
        # 格式: "type   name" 或 "type   name:N"
        # 按空格分割，最后一段是 field name (或 name:N)
        parts = stripped.split()
        if len(parts) < 2:
            continue

        field_part = parts[-1]
        type_part = ' '.join(parts[:-1])

        # 处理位域: name:N
        if ':' in field_part:
            field_name = field_part.split(':')[0]
        else:
            field_name = field_part

        bare_type = _strip_type_keywords(type_part)
        if bare_type and field_name and bare_type not in ('__attribute__', '__aligned__') and not bare_type.startswith('_'):
            fields.append((field_name, bare_type))

    return fields


def _load_pahole_cache() -> str:
    """加载预生成的 pahole dump（/tmp/pahole_full_dump.txt）。"""
    cache_path = "/tmp/pahole_full_dump.txt"
    if not hasattr(_load_pahole_cache, '_cache'):
        try:
            if os.path.exists(cache_path):
                with open(cache_path) as f:
                    _load_pahole_cache._cache = f.read()
            else:
                _load_pahole_cache._cache = ""
        except Exception:
            _load_pahole_cache._cache = ""
    return _load_pahole_cache._cache


def _get_or_build_fields(struct_name: str, dump: str) -> List[Tuple[str, str]]:
    """获取 struct 的字段列表（带缓存）。首次调用时预构建完整类型图。"""
    if not _type_graph:
        _build_full_type_graph()

    if struct_name in _type_graph:
        return _type_graph[struct_name]

    # 回退 BTF
    struct_def = _parse_struct_def(dump, struct_name)
    if not struct_def:
        _type_graph[struct_name] = []
        return []
    fields = _parse_struct_fields(struct_def)
    _type_graph[struct_name] = fields
    return fields


def _build_full_type_graph():
    """一次性从 pahole 缓存构建完整的 struct 类型图（88K struct）。"""
    pahole_cache = _load_pahole_cache()
    if not pahole_cache:
        return

    lines = pahole_cache.split('\n')
    current_name = None
    current_lines = []
    brace_depth = 0
    in_struct = False

    for line in lines:
        stripped = line.strip()
        if not in_struct:
            m = re.match(r'^struct\s+(\w+)\s*\{', stripped)
            if m:
                current_name = m.group(1)
                current_lines = [line]
                in_struct = True
                brace_depth = line.count('{') - line.count('}')
            continue

        current_lines.append(line)
        brace_depth += line.count('{') - line.count('}')
        if brace_depth <= 0:
            # struct 结束，解析字段
            struct_text = '\n'.join(current_lines)
            fields = _parse_pahole_fields(struct_text)
            _type_graph[current_name] = fields
            in_struct = False
            current_name = None
            current_lines = []

    print(f"  [btf_chain_enumerator] Built type graph: {len(_type_graph)} structs from pahole", file=sys.stderr)


def _resolve_type(type_name: str, dump: str) -> str:
    """解析 typedef 到实际类型（带缓存）。"""
    if type_name in _typedef_map:
        return _typedef_map[type_name]

    underlying = _get_typedef_target(dump, type_name)
    if underlying:
        _typedef_map[type_name] = underlying
        return underlying

    _typedef_map[type_name] = type_name
    return type_name


# ---------------------------------------------------------------------------
# 核心算法：BFS/DFS 枚举所有链
# ---------------------------------------------------------------------------

def _compute_reachability(target_type: str):
    """反向 BFS: 计算哪些 struct 类型能通过字段链到达 target_type。"""
    if not _type_graph:
        return
    # 反向索引: field_type → [struct_names_that_have_field_of_this_type]
    reverse = defaultdict(set)
    for sname, fields in _type_graph.items():
        for fname, ftype in fields:
            reverse[ftype].add(sname)

    # BFS from target
    reachable = {target_type}
    queue = deque([target_type])
    while queue:
        t = queue.popleft()
        for parent in reverse.get(t, set()):
            if parent not in reachable:
                reachable.add(parent)
                queue.append(parent)
    _reachability[target_type] = reachable


def enumerate_chains_from_type(
    struct_type: str,
    callee_type_chain: Optional[str] = None,
    btf_path: str = BTF_PATH,
    max_depth: int = MAX_DEPTH,
) -> List[Dict]:
    """
    从给定 struct 类型出发，枚举所有能到达 **callee 入口类型** 的字段路径。

    策略改变: 只搜到 callee_type_chain[0]（接头点），不搜到 atomic_t。
    拼接 callee 链在 cross_validator 中完成。

    Args:
        struct_type: 起始 struct 类型名（裸名，如 "kobject"）
        callee_type_chain: callee 的已知 type_chain。
                           如 "kref--refcount_struct--atomic_t"
                           搜索目标 = callee_type_chain 的第一段 "kref"
        btf_path: BTF 文件路径
        max_depth: 最大搜索深度

    Returns:
        [{
            "partial_type_chain": "kobject--kref",      # caller 内部的部分链
            "field_path": ["kref"],                      # 字段路径
            "matched_callee_entry": "kref",              # 匹配的 callee 入口类型
            "depth": 1,
        }, ...]
    """
    dump = _load_btf_c_dump(btf_path)
    # BTF dump 为空不影响 pahole/DWARF 枚举（使用预生成的缓存文件）

    # 解析搜索目标: callee_type_chain 的第一段
    target_type = None
    if callee_type_chain:
        callee_parts = [p.strip() for p in callee_type_chain.split("--")]
        target_type = callee_parts[0] if callee_parts else None
        target_type = _resolve_type(target_type, dump)

    # 解析起始类型（可能是 typedef）
    resolved_start = _resolve_type(struct_type, dump)

    # 触发布建类型图（必须在 _compute_reachability 之前，否则 _type_graph 为空）
    _get_or_build_fields(resolved_start, dump)

    # 计算 reachability（如果尚未计算）
    if target_type and target_type not in _reachability:
        _compute_reachability(target_type)

    results = []

    # 直接传参检查: caller_param_type == callee_entry_type（如 kref_get 的入参 kref 直接传给 refcount_inc）
    if target_type and resolved_start == target_type:
        results.append({
            "partial_type_chain": struct_type,
            "field_path": [],
            "matched_callee_entry": target_type,
            "depth": 0,
        })

    # DFS: (current_type, field_path, type_path, visited_types, depth)
    stack: List[Tuple[str, List[str], List[str], Set[str], int]] = [
        (resolved_start, [], [struct_type], {resolved_start}, 0)
    ]

    while stack:
        current_type, field_path, type_path, visited, depth = stack.pop()

        if depth >= max_depth:
            continue

        fields = _get_or_build_fields(current_type, dump)
        if not fields:
            continue

        for field_name, field_type_raw in fields:
            field_type_resolved = _resolve_type(field_type_raw, dump)

            # 匹配目标类型 → 找到接头点，记录部分链，停止深入
            if target_type and field_type_resolved == target_type:
                partial_chain = type_path + [field_type_resolved]
                results.append({
                    "partial_type_chain": "--".join(partial_chain),
                    "field_path": field_path + [field_name],
                    "matched_callee_entry": field_type_resolved,
                    "depth": depth + 1,
                })
                # 找到 callee 入口后停止，不继续深入
                continue

            # 剪枝: field_type_resolved 或其 typedef 解析后的类型必须可达 target
            if target_type:
                reachable_set = _reachability.get(target_type, set())
                if field_type_resolved not in reachable_set:
                    continue  # 剪枝
            if _get_or_build_fields(field_type_resolved, dump):
                if field_type_resolved not in visited:
                    new_visited = set(visited) | {field_type_resolved}
                    stack.append((
                        field_type_resolved,
                        field_path + [field_name],
                        type_path + [field_type_resolved],
                        new_visited,
                        depth + 1,
                    ))

    # 去重 + 按深度排序
    seen = set()
    unique = []
    for r in results:
        key = r["partial_type_chain"]
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda r: r["depth"])

    return unique


# ---------------------------------------------------------------------------
# 完整链验证：逐层确认 type_chain 在 BTF 中存在
# ---------------------------------------------------------------------------

def verify_full_chain_btf(type_chain: str, btf_path: str = BTF_PATH) -> Dict:
    """
    对一条完整的 type_chain 做 BTF 逐层验证。

    Args:
        type_chain: 完整链，如 "kobject--kref--refcount_struct--atomic_t"

    Returns:
        {"valid": True/False, "steps": [...], "first_mismatch": None}
    """
    dump = _load_btf_c_dump(btf_path)
    if not dump:
        return {"valid": False, "steps": [], "first_mismatch": "BTF dump failed"}

    parts = [p.strip() for p in type_chain.split("--")]
    if len(parts) < 2:
        return {"valid": False, "steps": [], "first_mismatch": "Chain too short"}

    steps = []
    for i in range(len(parts) - 1):
        struct_name = parts[i]
        next_type = parts[i + 1]

        # 跳过 atomic_t (terminal)
        if next_type == "atomic_t" and i == len(parts) - 2:
            steps.append({
                "step": i + 1,
                "struct": struct_name,
                "expect_field_type": next_type,
                "btf_confirms": True,
                "btf_field_name": "<terminal>",
            })
            continue

        # 标准化 next_type（解析 typedef，如 refcount_t → refcount_struct）
        next_resolved = _resolve_type(next_type, dump)

        # 查找 struct → field → type
        fields = _get_or_build_fields(struct_name, dump)
        found = False
        for fname, ftype in fields:
            resolved = _resolve_type(ftype, dump)
            if resolved == next_resolved:
                steps.append({
                    "step": i + 1,
                    "struct": struct_name,
                    "field": fname,
                    "field_type": resolved,
                    "btf_confirms": True,
                })
                found = True
                break

        if not found:
            steps.append({
                "step": i + 1,
                "struct": struct_name,
                "expect_field_type": next_type,
                "btf_confirms": False,
                "available_fields": [(f, _resolve_type(t, dump)) for f, t in fields[:5]],
            })
            return {
                "valid": False,
                "steps": steps,
                "first_mismatch": {
                    "step": i + 1,
                    "struct": struct_name,
                    "expected": next_type,
                }
            }

    return {"valid": True, "steps": steps, "first_mismatch": None}


# ---------------------------------------------------------------------------
# 高层接口：枚举所有 caller 参数/返回值的候选链
# ---------------------------------------------------------------------------

def enumerate_all_caller_chains(
    param_types: Dict[int, str],       # {param_index: type_name}  1-based
    return_type: Optional[str],         # 返回值类型名
    callee_type_chain: str,             # callee 的已知 type_chain
    param_names: Optional[Dict[int, str]] = None,  # {param_index: name}
    btf_path: str = BTF_PATH,
    max_depth: int = MAX_DEPTH,
) -> Dict[str, List[Dict]]:
    """
    对 caller 的所有参数和返回值，枚举候选 type_chain。

    Args:
        param_types: caller 参数类型映射 {1: "kobject", 2: "gfp_t"}
        return_type: caller 返回值类型名 (可为 None)
        callee_type_chain: callee 的已知 type_chain
        param_names: 参数名映射 {1: "kobj", 2: "flags"}

    Returns:
        {
            "params": {
                1: [  # param_index
                    {
                        "type_chain": "...",
                        "access_path": "kobj.kref.refcount.refs",
                        "field_path": ["kref", "refcount", "refs"],
                        "match_source": "...",
                    }, ...
                ],
            },
            "return": [...]  # 或不存在
        }
    """
    result = {"params": {}, "return": []}

    # 枚举每个参数
    for param_idx, ptype in param_types.items():
        resolved = _resolve_type(ptype, BTF_PATH) if hasattr(_resolve_type, '__code__') else ptype
        # _resolve_type needs dump loaded
        dump = _load_btf_c_dump(btf_path)
        resolved = _resolve_type(ptype, dump)
        chains = enumerate_chains_from_type(
            resolved, callee_type_chain, btf_path, max_depth
        )
        if chains:
            # 给每个链加上 access_path
            pname = (param_names or {}).get(param_idx, f"arg{param_idx}")
            for c in chains:
                c["access_path"] = pname + "." + ".".join(c["field_path"])
                c["via_param"] = param_idx
                c["param_name"] = pname
            result["params"][param_idx] = chains

    # 枚举返回值
    if return_type:
        dump = _load_btf_c_dump(btf_path)
        resolved = _resolve_type(return_type, dump)
        chains = enumerate_chains_from_type(
            resolved, callee_type_chain, btf_path, max_depth
        )
        if chains:
            for c in chains:
                c["access_path"] = "ret" + "." + ".".join(c["field_path"])
                c["via_return"] = True
            result["return"] = chains

    return result


# ---------------------------------------------------------------------------
# CLI 自检
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BTF chain enumerator")
    parser.add_argument("--type", default="kobject", help="Starting struct type")
    parser.add_argument("--callee-chain", default="kref--refcount_struct--atomic_t",
                        help="Callee type chain for filtering")
    parser.add_argument("--btf", default=BTF_PATH, help="BTF file path")
    parser.add_argument("--max-depth", type=int, default=MAX_DEPTH)

    args = parser.parse_args()

    print(f"Enumerating chains from '{args.type}' with filter '{args.callee_chain}'...")
    print(f"(BTF: {args.btf}, max_depth={args.max_depth})\n")

    chains = enumerate_chains_from_type(
        args.type, args.callee_chain, args.btf, args.max_depth
    )

    print(f"Found {len(chains)} candidate chain(s):\n")
    for i, c in enumerate(chains):
        print(f"  [{i+1}] type_chain: {c['type_chain']}")
        print(f"      fields:     {' -> '.join(c['field_path'])}")
        print(f"      depth:      {c['depth']}")
        print(f"      source:     {c['match_source']}")
        print()
