#!/usr/bin/env python3
"""
s9_v2_enrich_context.py — 富化版审计上下文准备

v2 核心改进:
  1. 查询函数报告 (FunctionResult) 获取 callee 的 get/put 行为
  2. 递归追踪 callee 的 callee (深度可配)
  3. 匹配 counter_path 与 callee member_access_path
  4. 自动分类: AUTO_FP_BALANCED / AUTO_FP_PURE_WRAPPER / NEEDS_REVIEW
  5. 输出富化的 Markdown 上下文，供 Claude Code 单轮审计

Usage:
    python3 s9_v2_enrich_context.py \
        --warns pass2_refcount_warns.txt \
        --func-dir FunctionResult/260620-all-2/ \
        --output-dir enriched_contexts/ \
        [--limit N] [--max-depth 3]
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
KERNEL_DIR = os.environ.get("REFCOUNT_KERNEL_DIR", "")
DEFAULT_FUNC_DIR = os.environ.get(
    "REFCOUNT_FUNCTION_RESULT_DIR",
    os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "FunctionResult", "default")
)

# 已知的 refcount 底层原语 — 不需要再向下追踪
REFCOUNT_PRIMITIVES = {
    'refcount_inc', 'refcount_dec', 'refcount_dec_and_test',
    'refcount_add', 'refcount_add_not_zero', 'refcount_set',
    'refcount_inc_not_zero', 'refcount_dec_not_one',
    'refcount_dec_if_one', 'refcount_dec_and_lock',
    'refcount_dec_and_mutex_lock', 'refcount_dec_and_rtnl_lock',
    'refcount_dec_and_lock_irqsave',
    'refcount_inc_not_zero_acquire', 'refcount_add_not_zero_acquire',
    'refcount_acquire_maybe_null', 'refcount_set_release',
    'atomic_inc', 'atomic_dec', 'atomic_dec_and_test',
    'atomic_add', 'atomic_sub', 'atomic_set',
    'kref_get', 'kref_put', 'kref_init',
    'kref_get_unless_zero', 'kref_put_lock', 'kref_put_mutex',
    'kobject_get', 'kobject_put',
    'get_device', 'put_device',
    '__devm_led_get', '__devm_reset_control_get',
    'devm_kzalloc', 'devm_kmalloc',
}

# 已知的非 refcount 函数 — 跳过
NON_REFCOUNT_FUNCTIONS = {
    'printk', 'pr_debug', 'pr_info', 'pr_err', 'pr_warn',
    'dev_err', 'dev_dbg', 'dev_info', 'dev_warn',
    'kfree', 'kmalloc', 'kzalloc', 'kcalloc', 'krealloc',
    'memset', 'memcpy', 'memmove', 'memcmp',
    'strlen', 'strcmp', 'strncmp', 'strcpy', 'strncpy',
    'snprintf', 'sprintf', 'scnprintf',
    'BUG', 'BUG_ON', 'WARN_ON', 'WARN_ON_ONCE',
    'likely', 'unlikely', 'IS_ERR', 'IS_ERR_OR_NULL',
    'PTR_ERR', 'ERR_PTR', 'container_of',
    'READ_ONCE', 'WRITE_ONCE', 'smp_rmb', 'smp_wmb', 'smp_mb',
    'mutex_lock', 'mutex_unlock', 'spin_lock', 'spin_unlock',
    'read_lock', 'read_unlock', 'write_lock', 'write_unlock',
    'rcu_read_lock', 'rcu_read_unlock',
    'list_add', 'list_del', 'INIT_LIST_HEAD',
    'if', 'while', 'for', 'switch', 'return', 'sizeof', 'typeof',
    'goto', 'break', 'continue', 'case', 'default',
    'int', 'void', 'char', 'struct', 'unsigned', 'long', 'static', 'const',
}


# ---------------------------------------------------------------------------
# 函数报告加载
# ---------------------------------------------------------------------------
class FuncReportDB:
    """加载并查询函数报告数据库"""

    def __init__(self, func_dir: str):
        self.func_dir = func_dir
        self._cache = {}       # func_name → report dict
        self._loaded = False
        self._load_time = 0

    def load(self):
        """预加载所有报告到内存"""
        if self._loaded:
            return
        t0 = time.time()
        count = 0
        for fname in os.listdir(self.func_dir):
            if not fname.endswith('.json'):
                continue
            func_name = fname[:-5]  # remove .json
            try:
                fpath = os.path.join(self.func_dir, fname)
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                self._cache[func_name] = data
                count += 1
            except (json.JSONDecodeError, IOError):
                continue
        self._loaded = True
        self._load_time = time.time() - t0
        print(f"  [FuncReportDB] Loaded {count} function reports in {self._load_time:.1f}s")

    def get(self, func_name: str) -> dict | None:
        """获取函数报告，未找到返回 None"""
        return self._cache.get(func_name)

    def get_callee_info(self, func_name: str) -> list[dict]:
        """获取函数的 callee refcount 信息列表"""
        report = self.get(func_name)
        if not report:
            return []
        return report.get('callee_func_info_list', [])

    def get_purity(self, func_name: str) -> str:
        report = self.get(func_name)
        if not report:
            return 'unknown'
        return report.get('final', {}).get('purity', report.get('purity', 'unknown'))

    def get_conditionality(self, func_name: str) -> str:
        report = self.get(func_name)
        if not report:
            return 'unknown'
        return report.get('final', {}).get('conditionality',
                report.get('conditionality', 'unknown'))

    def is_wrapper(self, func_name: str) -> bool:
        report = self.get(func_name)
        if not report:
            return False
        return report.get('final', {}).get('is_wrapper',
                report.get('is_wrapper', False))

    def get_contract_summary(self, func_name: str) -> str:
        report = self.get(func_name)
        if not report:
            return ''
        return report.get('final', {}).get('contract_summary',
                report.get('contract_summary', ''))


# ---------------------------------------------------------------------------
# 源码获取 (复用 s9 逻辑)
# ---------------------------------------------------------------------------
def read_file_lines(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()


def find_function_source(filepath: str, func_name: str) -> tuple[str, int] | None:
    """在指定文件中查找函数体，返回 (源码, 起始行号) 或 None"""
    lines = read_file_lines(filepath)
    if not lines:
        return None

    # 匹配函数定义行
    patterns = [
        rf'^(?:static\s+|inline\s+|__\w+\s+|const\s+)*'
        rf'(?:struct\s+\w+\s*\*?\s*|void\s+|int\s+|bool\s+|long\s+|unsigned\s+\w+\s+|size_t\s+|ssize_t\s+|'
        rf'\w+\s*\*?\s+){re.escape(func_name)}\s*\(',
        rf'^{re.escape(func_name)}\s*\(',
    ]

    for i, ln in enumerate(lines):
        for pat in patterns:
            if re.match(pat, ln):
                out = []
                depth = 0
                started = False
                for ii in range(i, min(len(lines), i + 800)):
                    ln2 = lines[ii]
                    out.append(f"{ii+1}: {ln2.rstrip()}")
                    if not started:
                        if '{' in ln2:
                            started = True
                            depth += ln2.count('{') - ln2.count('}')
                    else:
                        depth += ln2.count('{') - ln2.count('}')
                        if depth <= 0:
                            break
                return ('\n'.join(out), i + 1)
    return None


def find_function_source_anywhere(func_name: str, kernel_dir: str) -> tuple[str, str, int] | None:
    """在内核源码中查找函数，返回 (文件路径, 源码, 起始行号)"""
    # 优先 cscope
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from accurate_func_locator import AccurateFuncLocator
        locator = AccurateFuncLocator(kernel_dir)
        if locator.cscope_db_exists():
            result = locator.find_function_source(func_name)
            if result and result.get('confidence') in ('high', 'medium'):
                src = result.get('source_code', '')
                start = result.get('start_line', 1)
                fpath = result.get('file', '')
                numbered = []
                for li, ln in enumerate(src.split('\n')):
                    numbered.append(f"{start + li}: {ln}")
                return (fpath, '\n'.join(numbered), start)
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Callee 提取 & 递归分析
# ---------------------------------------------------------------------------
def extract_callees_from_source(source: str) -> set[str]:
    """从函数源码中提取被调用的函数名"""
    callees = set()
    for line in source.split('\n'):
        # 去掉行号前缀
        content = re.sub(r'^\s*\d+:\s*', '', line)
        # 去掉注释
        content = re.sub(r'//.*$', '', content)
        content = re.sub(r'/\*.*?\*/', '', content)
        for m in re.finditer(r'\b([a-zA-Z_]\w{1,40})\s*\(', content):
            fn = m.group(1)
            if fn not in NON_REFCOUNT_FUNCTIONS and not fn.startswith('__'):
                callees.add(fn)
    return callees


def get_context_around(lines: list, target_lines: list, window: int = 10) -> str:
    """提取目标行附近的代码窗口 (包含注释)"""
    ctx = set()
    for gl in target_lines:
        for li in range(max(0, gl - window), min(len(lines), gl + window + 1)):
            ctx.add(li)
    if not ctx:
        return ""
    out = []
    prev = -2
    for li in sorted(ctx):
        if li > prev + 1:
            out.append("  ...")
        out.append(f"{li+1}: {lines[li].rstrip()}")
        prev = li
    return '\n'.join(out)


def extract_relevant_comments(lines: list, target_lines: list, radius: int = 25) -> str:
    """提取目标行附近与 refcount/生命周期 相关的注释

    包括:
      - /* ... */ 块注释
      - // 行注释
      - 包含关键词: refcount, kref, get, put, release, free, cleanup,
                    owner, transfer, managed, devm, callback, work,
                    async, defer, life, 引用, 释放, 所有权
    """
    keywords = [
        'refcount', 'kref', 'get', 'put', 'release', 'free', 'cleanup',
        'owner', 'transfer', 'managed', 'devm', 'callback', 'work',
        'async', 'defer', 'life', 'alloc', 'destroy', 'register', 'unregister',
        '引用', '释放', '所有权', 'acquire', 'increment', 'decrement',
        'hold', 'drop', 'init', 'exit', 'remove', 'probe',
    ]

    relevant = []
    seen_lines = set()

    for gl in target_lines:
        for li in range(max(0, gl - radius), min(len(lines), gl + radius + 1)):
            if li in seen_lines:
                continue
            line = lines[li].rstrip()

            # 检查是否包含注释
            has_comment = '/*' in line or '*/' in line or '//' in line
            if not has_comment:
                continue

            # 检查是否包含关键词
            line_lower = line.lower()
            if not any(kw in line_lower for kw in keywords):
                continue

            seen_lines.add(li)
            relevant.append((li + 1, line))

    if not relevant:
        return ""

    # 按行号排序，相邻行合并为块
    relevant.sort()
    out = []
    prev = -2
    for lineno, text in relevant:
        if lineno > prev + 1:
            out.append("")  # 空行分隔
        out.append(f"{lineno}: {text}")
        prev = lineno
    return '\n'.join(out).strip()


# ---------------------------------------------------------------------------
# 主逻辑: 单条告警的富化
# ---------------------------------------------------------------------------
def parse_warning(line: str) -> dict | None:
    """解析 pass2_refcount_warns.txt 的一行 (支持 leak/inconsistent/excess_put/UAF)"""
    # Refcount: leak, inconsistent, excess put
    m = re.match(
        r'(?:\d+:)?([^:]+):(\d+)\s+(\S+)\(\)\s+warn:\s+'
        r'(refcount leak|inconsistent refcounting|refcount excess put)\s+\'([^\']+)\''
        r'(?::\s+lines=\'([^\']*)\')?', line.strip())
    if m:
        return {
            "file": m.group(1),
            "line": int(m.group(2)),
            "function": m.group(3),
            "warn_type": m.group(4),
            "counter_path": m.group(5),
            "get_lines": m.group(6) or "",
            "_raw": line.strip(),
        }
    # UAF: using/passing/dereferencing/returning after refcount release
    m = re.match(
        r'(?:\d+:)?([^:]+):(\d+)\s+(\S+)\(\)\s+(error|warn):\s+'
        r'(using|passing|dereferencing|returning)\s+\'([^\']+)\'\s+'
        r'after\s+(?:possible\s+)?refcount release\s*\(line\s+(\d+)\)', line.strip())
    if m:
        return {
            "file": m.group(1),
            "line": int(m.group(2)),
            "function": m.group(3),
            "warn_type": f"uaf_{m.group(5)}",
            "counter_path": m.group(6),
            "get_lines": m.group(7) or "",
            "_raw": line.strip(),
        }
    return None


def _normalize_path(p: str) -> str:
    """标准化 member_access_path 用于比较"""
    # 去掉 $-> 前缀，去掉数组下标，去掉空格
    p = re.sub(r'^\$->', '', p)
    p = re.sub(r'\[\d*\]', '', p)
    p = re.sub(r'\s+', '', p)
    return p.lower()


def _paths_match(counter_path: str, callee_path: str) -> bool:
    """判断 counter_path 和 callee 的 access_path 是否匹配"""
    cp = _normalize_path(counter_path)
    ap = _normalize_path(callee_path)
    if not cp or not ap:
        return False
    # 完全匹配 或 一方包含另一方
    if cp == ap:
        return True
    if cp in ap or ap in cp:
        return True
    # 比较后缀 (refcount.refs.counter, refs.counter 等)
    cp_parts = cp.split('.')
    ap_parts = ap.split('.')
    # 至少最后 2 个部分匹配
    for n in range(2, min(len(cp_parts), len(ap_parts)) + 1):
        if cp_parts[-n:] == ap_parts[-n:]:
            return True
    return False


def enrich_single(w: dict, db: FuncReportDB, kernel_dir: str,
                  max_depth: int = 3) -> dict:
    """为单条告警构建富化上下文"""
    result = {
        "warning": w,
        "main_source": "",
        "main_start_line": 0,
        "get_context": "",
        "relevant_comments": "",   # 新增: 告警行附近的注释
        "callee_source": {},       # 新增: 关键callee源码
        "callee_analysis": [],  # [(func_name, report_data, depth)]
        "refcount_flow": {"gets": [], "puts": [], "unknowns": []},
        "auto_classification": "NEEDS_REVIEW",
        "auto_reason": "",
    }

    # --- Step 1: 主函数源码 ---
    filepath = os.path.join(kernel_dir, w['file'])
    if os.path.exists(filepath):
        fs = find_function_source(filepath, w['function'])
    else:
        fs = None
    if not fs:
        fs = find_function_source_anywhere(w['function'], kernel_dir)
    if fs:
        result['main_source'] = fs[0]
        result['main_start_line'] = fs[1]
    else:
        result['auto_classification'] = "SOURCE_NOT_FOUND"
        result['auto_reason'] = f"Cannot find {w['function']}() source"
        return result

    # --- Step 2: Get-site 上下文 ---
    all_lines = read_file_lines(filepath)
    glines = []
    if w['get_lines']:
        glines = [int(x) for x in w['get_lines'].split(',') if x.strip().isdigit()]
    if glines:
        result['get_context'] = get_context_around(all_lines, glines)

    # --- Step 2b: 提取告警行附近的相关注释 ---
    target_lines = [w['line']] + glines
    result['relevant_comments'] = extract_relevant_comments(all_lines, target_lines)

    # --- Step 3: 提取 callee 并递归查询 ---
    callees_in_func = extract_callees_from_source(result['main_source'])
    visited = set()
    to_visit = [(fn, 0) for fn in callees_in_func]  # (func_name, depth)

    while to_visit:
        fn, depth = to_visit.pop(0)
        if fn in visited or depth > max_depth:
            continue
        visited.add(fn)

        report = db.get(fn)
        if not report:
            # 底层原语不需要报告
            if fn in REFCOUNT_PRIMITIVES:
                result['callee_analysis'].append({
                    'name': fn, 'depth': depth,
                    'has_report': False, 'is_primitive': True,
                    'get_or_put': 'primitive',
                    'member_path': '',
                    'purity': 'high',
                    'conditionality': 'unconditional',
                    'is_wrapper': True,
                    'callees': [],
                })
            continue

        # 解析报告
        callee_list = report.get('callee_func_info_list', [])
        final = report.get('final', {})
        purity = final.get('purity', report.get('purity', 'unknown'))
        conditionality = final.get('conditionality', report.get('conditionality', 'unknown'))
        is_wrapper = final.get('is_wrapper', report.get('is_wrapper', False))
        contract = final.get('contract_summary', report.get('contract_summary', ''))

        entry = {
            'name': fn, 'depth': depth,
            'has_report': True, 'is_primitive': False,
            'purity': purity,
            'conditionality': conditionality,
            'is_wrapper': is_wrapper,
            'contract': contract,
            'callees': [],
        }

        for ci in callee_list:
            cname = ci.get('callee_function_name', '')
            gop = ci.get('get_or_put', '')
            mpath = ci.get('member_access_path', '')
            mtype = ci.get('member_type_chain', '')
            entry['callees'].append({
                'name': cname, 'get_or_put': gop,
                'member_path': mpath, 'member_type': mtype,
            })

            # 记录匹配的 get/put
            if gop in ('get', 'put') and mpath:
                matched = _paths_match(w['counter_path'], mpath)
                if matched:
                    result['refcount_flow'][f'{gop}s'].append({
                        'function': fn,
                        'callee': cname,
                        'path': mpath,
                        'matched': True,
                    })
                else:
                    # 即使不匹配也记录，可能通过指针别名关联
                    result['refcount_flow'][f'{gop}s'].append({
                        'function': fn,
                        'callee': cname,
                        'path': mpath,
                        'matched': False,
                    })

            # 递归: 把 callee 的 callee 加入访问队列
            if depth < max_depth and cname not in visited and cname not in REFCOUNT_PRIMITIVES:
                to_visit.append((cname, depth + 1))

        result['callee_analysis'].append(entry)

    # --- Step 4: 自动分类 ---
    # --- Step 5: 提取关键 callee 源码 (从 warning 的 fn: inc/dec 列表) ---
    inc_dec_funcs = set()
    # 从原始 warning line 文本中提取 (最可靠)
    warn_text = w.get('_raw', '')
    inc_match = re.search(r'inc:\[([^\]]*)\]', warn_text)
    dec_match = re.search(r'dec:\[([^\]]*)\]', warn_text)
    if inc_match:
        for f in inc_match.group(1).split(','):
            inc_dec_funcs.add(f.strip())
    if dec_match:
        for f in dec_match.group(1).split(','):
            inc_dec_funcs.add(f.strip())
    # 也加入 callee_analysis 中的直接 callee
    for c in result['callee_analysis']:
        if not c.get('has_report'):
            inc_dec_funcs.add(c['name'])

    for fn in inc_dec_funcs:
        if fn in REFCOUNT_PRIMITIVES:
            continue
        if db.get(fn):
            continue  # 有报告的跳过

    # 使用 cscope 获取 callee 源码 (快速精准)
    callee_count = 0
    for fn in sorted(inc_dec_funcs):
        if callee_count >= 8:
            break
        if fn in REFCOUNT_PRIMITIVES or db.get(fn):
            continue

        src = None
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from accurate_func_locator import AccurateFuncLocator
            locator = AccurateFuncLocator(kernel_dir)
            if locator.cscope_db_exists():
                r = locator.find_function_source(fn)
                if r and r.get('confidence') in ('high', 'medium'):
                    raw_src = r.get('source_code', '')
                    start = r.get('start_line', 1)
                    numbered = []
                    for li, ln in enumerate(raw_src.split('\n')):
                        numbered.append(f"{start + li}: {ln}")
                    src = '\n'.join(numbered)
                    callee_count += 1
        except Exception:
            pass

        if src:
            result['callee_source'][fn] = src

    result['auto_classification'], result['auto_reason'] = _classify(w, result)

    return result


def _classify(w: dict, r: dict) -> tuple[str, str]:
    """基于富化分析自动分类"""
    flow = r['refcount_flow']
    matched_gets = [g for g in flow['gets'] if g['matched']]
    matched_puts = [p for p in flow['puts'] if p['matched']]
    all_matched = [g for g in flow['gets'] if g['matched']] + [p for p in flow['puts'] if p['matched']]

    # 如果没找到任何匹配的 callee
    if not all_matched:
        return ('NEEDS_REVIEW',
                'No callee with matching member_access_path found in function reports. '
                'Counter path may involve non-wrapper functions not covered by reports.')

    # 如果 get 和 put 数量相同，且所有 callee 都是高纯度 wrapper
    purity_values = {c['purity'] for c in r['callee_analysis'] if c['has_report']}
    if (len(matched_gets) == len(matched_puts) and matched_gets and matched_puts
            and purity_values == {'high'}):
        return ('AUTO_FP_BALANCED',
                f'All {len(all_matched)} matched callees are high-purity wrappers with balanced get/put')

    # 如果只有 get 没有 put → 可能的 leak
    if matched_gets and not matched_puts:
        gets_desc = ', '.join(f"{g['function']}()→{g['callee']}()" for g in matched_gets[:5])
        return ('NEEDS_REVIEW',
                f'Only GET operations found (no PUT): {gets_desc}. '
                f'Need to verify if put happens through other paths or if this is a real leak.')

    # 如果只有 put 没有 get → 可能的 underflow (通常是 smatch 误报)
    if matched_puts and not matched_gets:
        puts_desc = ', '.join(f"{p['function']}()→{p['callee']}()" for p in matched_puts[:5])
        return ('NEEDS_REVIEW',
                f'Only PUT operations found (no GET): {puts_desc}. '
                f'May indicate smatch tracking issue or actual use-after-put.')

    return ('NEEDS_REVIEW', 'Mixed get/put pattern found, manual analysis required.')


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
# 已知 inline 函数的 refcount 契约 (不在函数报告库中)
KNOWN_INLINE_CONTRACTS = {
    'pm_runtime_get_sync': {
        'contract': 'Increments dev->power.usage_count via __pm_runtime_resume. '
                     'Returns 1/0 on success (count incremented), negative on error (count may NOT be incremented). '
                     'CRITICAL: caller MUST check return value! If return < 0, no count was added.',
        'warning': 'If return value is NOT checked, assume success path → count IS incremented → error paths need put!',
    },
    'pm_runtime_get': {
        'contract': 'Same as pm_runtime_get_sync: increments power.usage_count on success. '
                     'Return value MUST be checked.',
    },
    'pm_runtime_resume_and_get': {
        'contract': 'Increments power.usage_count and resumes device. Returns 0 on success, negative on error. '
                     'On success, count IS incremented. On error, count is NOT incremented.',
    },
    'pm_runtime_put_sync': {
        'contract': 'Decrements dev->power.usage_count. Unconditional — always decrements.',
    },
    'pm_runtime_put_sync_autosuspend': {
        'contract': 'Decrements dev->power.usage_count with autosuspend. Always decrements.',
    },
    'snd_power_ref': {
        'contract': 'Increments card->power_ref via atomic_inc. UNCONDITIONAL — always increments. '
                     'Caller MUST pair with snd_power_unref.',
    },
    'snd_power_ref_and_wait': {
        'contract': 'CONDITIONAL: increments card->power_ref ONLY on success (return 0). '
                     'Returns negative on error — count NOT incremented. '
                     'CRITICAL: if return != 0, no ref held, do NOT call snd_power_unref.',
        'warning': 'Only get on success (return 0). Error path has NO ref to release.',
    },
    'snd_power_unref': {
        'contract': 'Decrements card->power_ref via atomic_dec. Always decrements.',
    },
    'reset_control_deassert': {
        'contract': 'Increments rst->deassert_count. Caller must pair with reset_control_assert.',
    },
    'reset_control_assert': {
        'contract': 'Decrements rst->deassert_count.',
    },
    'chcr_inc_wrcount': {
        'contract': 'CONDITIONAL: increments dev->inflight ONLY if dev->state != CHCR_DETACH. '
                     'Returns 0 on success (count inc), 1 on skip (DETACH state, no inc). '
                     'CRITICAL: if return != 0, no count was added.',
        'warning': 'Only increments when state != DETACH. Check return value before assuming count was added.',
    },
    'chcr_dec_wrcount': {
        'contract': 'Decrements dev->inflight via atomic_dec. Always decrements.',
    },
    'iwpm_get_nlmsg_request': {
        'contract': 'Allocates and initializes nlmsg_request with kref_init + kref_get. '
                     'Returns object with refcount = 1. Caller must release via iwpm_free_nlmsg_request or kref_put.',
    },
    'iwpm_free_nlmsg_request': {
        'contract': 'kref_put callback — releases the nlmsg_request when refcount reaches 0.',
    },
}

def _extract_inc_dec_from_warning(w: dict) -> tuple[list, list]:
    """从 warning 的原始行中解析 inc:[...] dec:[...] 函数列表"""
    raw = w.get('_raw', '')
    import re
    incs = []
    decs = []
    m = re.search(r'inc:\[([^\]]*)\]', raw)
    if m:
        incs = [x.strip() for x in m.group(1).split(',') if x.strip()]
    m = re.search(r'dec:\[([^\]]*)\]', raw)
    if m:
        decs = [x.strip() for x in m.group(1).split(',') if x.strip()]
    return incs, decs


def _build_contract_summary(r: dict) -> list[dict]:
    """构建 get/put 契约摘要：从 smatch inc/dec 函数列表 + 函数报告 + 已知 inline 契约"""
    contracts = []
    seen_funcs = set()

    # 1. 从 smatch 告警行解析 inc/dec 函数名
    inc_fns, dec_fns = _extract_inc_dec_from_warning(r.get('warning', {}))

    # 2. 从 refcount_flow 补充
    flow = r.get('refcount_flow', {})
    for g in flow.get('gets', []):
        fn = g.get('function', '')
        if fn and fn not in inc_fns:
            inc_fns.append(fn)
    for p in flow.get('puts', []):
        fn = p.get('function', '')
        if fn and fn not in dec_fns:
            dec_fns.append(fn)

    all_ops = [('🔺 GET', f) for f in inc_fns] + [('🔻 PUT', f) for f in dec_fns]

    for role, fname in all_ops:
        if not fname or fname in seen_funcs:
            continue
        seen_funcs.add(fname)

        entry = None

        # a) 从函数报告 DB 获取
        for c in r.get('callee_analysis', []):
            if c.get('name') == fname and c.get('contract'):
                entry = {'role': role, 'function': fname, 'contract': c['contract']}
                break

        # b) 从已知 inline 契约获取
        if not entry and fname in KNOWN_INLINE_CONTRACTS:
            kc = KNOWN_INLINE_CONTRACTS[fname]
            entry = {'role': role, 'function': fname, 'contract': kc['contract']}
            if kc.get('warning'):
                entry['warning'] = kc['warning']

        # c) 从函数报告 DB 中按 callee 名查找
        if not entry:
            for c in r.get('callee_analysis', []):
                for sc in c.get('callees', []):
                    if sc.get('name') == fname and c.get('contract'):
                        entry = {'role': role, 'function': fname, 'contract': c['contract']}
                        break
                if entry:
                    break

        if entry:
            contracts.append(entry)

    return contracts


def format_context_markdown(r: dict, index: int) -> str:
    """将富化分析结果格式化为 Markdown"""
    w = r['warning']
    flow = r['refcount_flow']
    lines = []

    lines.append(f"# Audit #{index}: {w['file']}:{w['line']} {w['function']}()")
    lines.append("")

    # ── Warning Info ──
    lines.append("## Warning Info")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| File | `{w['file']}` |")
    lines.append(f"| Line | {w['line']} |")
    lines.append(f"| Function | `{w['function']}()` |")
    lines.append(f"| Warn Type | **{w['warn_type']}** |")
    lines.append(f"| Counter Path | `{w['counter_path']}` |")
    lines.append(f"| Get Lines | {w['get_lines'] or 'N/A'} |")
    lines.append(f"| Auto Classification | **{r['auto_classification']}** |")
    lines.append(f"| Auto Reason | {r['auto_reason']} |")
    lines.append("")

    # ── Refcount Flow Summary ──
    all_matched = [g for g in flow['gets'] if g['matched']] + [p for p in flow['puts'] if p['matched']]
    if all_matched:
        lines.append("## Refcount Flow (Matched Callees)")
        lines.append("")
        lines.append("| Role | Wrapper Function | Callee | Member Path | Matched |")
        lines.append("|------|-----------------|--------|-------------|---------|")
        for g in flow['gets']:
            icon = '✓' if g['matched'] else '?'
            lines.append(f"| 🔺 GET | `{g['function']}()` | `{g['callee']}()` | `{g['path']}` | {icon} |")
        for p in flow['puts']:
            icon = '✓' if p['matched'] else '?'
            lines.append(f"| 🔻 PUT | `{p['function']}()` | `{p['callee']}()` | `{p['path']}` | {icon} |")
        lines.append("")

    # ── 🔴 Get/Put Contract Summary ──
    # Extract contracts for all matched get/put callees (from reports + known inline APIs)
    contracts = _build_contract_summary(r)
    if contracts:
        lines.append("## 🔴 Get/Put Contract Summary (MUST READ)")
        lines.append("")
        lines.append("_These contracts explain EXACTLY what each get/put function does to the refcount._")
        lines.append("_Pay attention to: conditional vs unconditional, return value semantics, error path behavior._")
        lines.append("")
        for c in contracts:
            lines.append(f"- **{c['role']}** `{c['function']}()`: {c['contract']}")
            if c.get('warning'):
                lines.append(f"  - ⚠️ {c['warning']}")
        lines.append("")

    # ── Callee Analysis (函数报告详情) ──
    callees_with_reports = [c for c in r['callee_analysis'] if c['has_report']]
    if callees_with_reports:
        lines.append("## Callee Function Report Details")
        lines.append("")
        lines.append("| Function | Depth | Purity | Wrapper | Conditionality | Key Callees |")
        lines.append("|----------|-------|--------|---------|---------------|-------------|")
        for c in callees_with_reports:
            sub_callees = ', '.join(
                f"{sc['name']}({sc['get_or_put']})"
                for sc in c['callees'][:5]
            )
            if len(c['callees']) > 5:
                sub_callees += f", ... (+{len(c['callees'])-5})"
            wrapper_str = '✅' if c['is_wrapper'] else '❌'
            lines.append(
                f"| `{c['name']}()` | {c['depth']} | {c['purity']} | {wrapper_str} "
                f"| {c['conditionality']} | {sub_callees or '—'} |"
            )
            if c['contract']:
                lines.append(f"| | | | | | _Contract:_ {c['contract'][:120]} |")
        lines.append("")

    # ── Main Function Source ──
    lines.append("## Main Function Source")
    lines.append(f"_`{w['file']}`, starts near line {r['main_start_line']}_")
    lines.append("")
    lines.append("```c")
    lines.append(r['main_source'])
    lines.append("```")
    lines.append("")

    # ── Get-Site Context ──
    if r['get_context']:
        lines.append("## Get-Site Context")
        lines.append(f"_Lines near get-sites: {w['get_lines']}_")
        lines.append("")
        lines.append("```c")
        lines.append(r['get_context'])
        lines.append("```")
        lines.append("")

    # ── Key Callee Source Code ──
    # 为 inc/dec 列表中无函数报告的 callee 提供源码
    callee_source_info = r.get('callee_source', {})
    if callee_source_info:
        lines.append("## 🔍 Key Callee Source Code")
        lines.append("")
        lines.append("_These are the actual implementations of refcount operations_")
        lines.append("_referenced in the warning. Read them to understand exact behavior._")
        lines.append("")
        for cname, csrc in sorted(callee_source_info.items()):
            lines.append(f"### `{cname}()`")
            lines.append("```c")
            lines.append(csrc)
            lines.append("```")
            lines.append("")
        lines.append("**⚠️ Use these implementations to verify:**")
        lines.append("- Does the inc function ALWAYS increment before returning success?")
        lines.append("- Does the inc function ever increment AND return an error?")
        lines.append("- Does the dec function have any side effects?")
        lines.append("")

    # ── Relevant Comments ──
    if r.get('relevant_comments'):
        lines.append("## 📝 Relevant Comments Near Warning Site")
        lines.append("")
        lines.append("_Comments from the source code that may explain refcount semantics,_")
        lines.append("_ownership transfer, managed cleanup, or async behavior._")
        lines.append("")
        lines.append("```c")
        lines.append(r['relevant_comments'])
        lines.append("```")
        lines.append("")
        lines.append("**⚠️ AUDITOR: Read these comments carefully!**")
        lines.append("They often contain critical information about:")
        lines.append("- Whether a refcount is transferred to another object")
        lines.append("- Whether cleanup is managed (devm, auto-cleanup)")
        lines.append("- Whether release is deferred (callback, work_struct)")
        lines.append("- The intended lifecycle of the refcounted object")
        lines.append("")

    # ── Audit Instructions ──
    lines.append("## Audit Instructions")
    lines.append("")
    lines.append("Analyze the above information and determine:")
    lines.append("1. **Refcount Lifecycle**: Where is the refcount acquired and released?")
    lines.append("2. **Return Path Analysis**: Is the refcount properly managed on ALL return paths?")
    lines.append("3. **Callee Verification**: Verify each callee's get/put behavior from the reports above.")
    lines.append("4. **False Positive Patterns**: Check for common FP patterns:")
    lines.append("   - Ownership transfer (callee stores reference for later release)")
    lines.append("   - Managed resources (`devm_*`, auto-cleanup)")
    lines.append("   - IS_ERR guard (error path has no refcount to leak)")
    lines.append("   - Async/deferred release (refcount released in callback)")
    lines.append("   - `balanced refcount` already verified by smatch")
    lines.append("")
    lines.append("Output your verdict in this format:")
    lines.append("")
    lines.append("```")
    lines.append("## VERDICT: {REAL_BUG | FALSE_POSITIVE}")
    lines.append("### Confidence: {HIGH | MEDIUM | LOW}")
    lines.append("### Reasoning")
    lines.append("{Detailed analysis}")
    lines.append("### False Positive Pattern (if applicable)")
    lines.append("{Which FP pattern matches, or N/A}")
    lines.append("### Fix (if REAL_BUG)")
    lines.append("{Minimal code change suggestion, or N/A}")
    lines.append("```")
    lines.append("")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='s9_v2: Enriched audit context preparation')
    parser.add_argument('--warns', required=True, help='pass2_refcount_warns.txt path')
    parser.add_argument('--func-dir', default=DEFAULT_FUNC_DIR, help='Function report directory')
    parser.add_argument('--output-dir', required=True, help='Output directory for enriched contexts')
    parser.add_argument('--kernel-dir', default=KERNEL_DIR, help='Kernel source directory')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of warnings')
    parser.add_argument('--max-depth', type=int, default=3, help='Max recursion depth for callee tracing')
    args = parser.parse_args()

    # ── 加载函数报告 ──
    print("=" * 60)
    print("s9_v2: Enriched Context Preparation")
    print("=" * 60)
    db = FuncReportDB(args.func_dir)
    db.load()

    # ── 解析告警 ──
    warnings = []
    with open(args.warns) as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            p = parse_warning(ln)
            if p:
                warnings.append(p)

    print(f"  Parsed {len(warnings)} warnings from {args.warns}")
    if args.limit > 0:
        warnings = warnings[:args.limit]
        print(f"  Limited to {args.limit} warnings")

    # ── 创建输出目录 ──
    os.makedirs(args.output_dir, exist_ok=True)

    # ── 批量处理 ──
    stats = defaultdict(int)
    results = []

    for i, w in enumerate(warnings):
        r = enrich_single(w, db, args.kernel_dir, args.max_depth)
        results.append(r)
        stats[r['auto_classification']] += 1

        # 输出富化上下文
        safe_name = f"{w['file'].replace('/','_')}_{w['line']}_{w['function']}"
        out_file = os.path.join(args.output_dir, f"{i+1:04d}_{safe_name}.md")
        md = format_context_markdown(r, i + 1)
        with open(out_file, 'w') as f:
            f.write(md)

        if (i + 1) % 50 == 0 or i == 0:
            n_gets = len(r['refcount_flow']['gets'])
            n_puts = len(r['refcount_flow']['puts'])
            print(f"  [{i+1}/{len(warnings)}] {w['file']}:{w['line']} {w['function']}()"
                  f" → {r['auto_classification']} "
                  f"(gets={n_gets}, puts={n_puts})")

    # ── 统计汇总 ──
    print(f"\n{'='*60}")
    print(f"Enrichment Complete: {len(results)} contexts")
    print(f"{'='*60}")
    print(f"  AUTO_FP_BALANCED:      {stats.get('AUTO_FP_BALANCED', 0)}")
    print(f"  AUTO_FP_PURE_WRAPPER:  {stats.get('AUTO_FP_PURE_WRAPPER', 0)}")
    print(f"  NEEDS_REVIEW:          {stats.get('NEEDS_REVIEW', 0)}")
    print(f"  SOURCE_NOT_FOUND:      {stats.get('SOURCE_NOT_FOUND', 0)}")
    print(f"  Output: {args.output_dir}/")

    # ── 写入摘要文件 ──
    summary_file = os.path.join(args.output_dir, '_auto_classification_summary.md')
    with open(summary_file, 'w') as f:
        f.write("# Auto-Classification Summary\n\n")
        f.write(f"Total warnings: {len(results)}\n\n")
        f.write("| Classification | Count | Percentage |\n")
        f.write("|----------------|-------|------------|\n")
        for cls in ['AUTO_FP_BALANCED', 'AUTO_FP_PURE_WRAPPER', 'NEEDS_REVIEW', 'SOURCE_NOT_FOUND']:
            cnt = stats.get(cls, 0)
            pct = f"{100*cnt/len(results):.1f}%" if results else "0%"
            f.write(f"| {cls} | {cnt} | {pct} |\n")
        f.write("\n## Per-Warning Details\n\n")
        for r in results:
            w = r['warning']
            f.write(f"- `{w['file']}:{w['line']}` `{w['function']}()` "
                    f"→ **{r['auto_classification']}**: {r['auto_reason']}\n")
    print(f"  Summary: {summary_file}")


if __name__ == '__main__':
    main()
