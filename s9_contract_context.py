#!/usr/bin/env python3
"""
s9_v3_contract_context.py — 极简审计上下文：仅告警+源码+get/put契约

v3 设计原则: 保持简洁，只提供 AI 需要的信息，让它自己决定查什么源码。
  - 不预加载 callee 源码（交给 AI 交互式 [NEED_SOURCE]）
  - 不递归追踪 wrapper（交给 AI）
  - 只提供 get/put 函数的契约摘要（最关键的信息）

Usage:
    python3 s9_v3_contract_context.py --warns warns.txt --func-dir FunctionResult/ --output-dir contexts/
"""

import argparse, json, os, re, sys

KERNEL_DIR = os.environ.get("REFCOUNT_KERNEL_DIR", "")
DEFAULT_FUNC_DIR = os.environ.get(
    "REFCOUNT_FUNCTION_RESULT_DIR",
    os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "FunctionResult", "default")
)

# 已知 inline/宏函数的 refcount 契约 (不在函数报告DB中)
KNOWN_CONTRACTS = {
    'pm_runtime_get_sync': '🔺 GET: increments power.usage_count. Returns 1/0=success(count+1), <0=error(no inc). '
                           '⚠️ If return value NOT checked → assume success → error paths MUST put!',
    'pm_runtime_get': '🔺 GET: same as get_sync. Check return value!',
    'pm_runtime_resume_and_get': '🔺 GET: increments power.usage_count on success(return 0). Error→no inc.',
    'pm_runtime_put_sync': '🔻 PUT: decrements power.usage_count. Always runs.',
    'pm_runtime_put_sync_autosuspend': '🔻 PUT: decrements power.usage_count. Always runs.',
    'snd_power_ref': '🔺 GET: UNCONDITIONAL atomic_inc(&card->power_ref). Always increments. MUST pair with snd_power_unref.',
    'snd_power_ref_and_wait': '🔺 GET: UNCONDITIONAL. Calls snd_power_ref(card)→atomic_inc BEFORE any wait/check. Ref IS held on ALL return paths (including -ENODEV). Caller MUST snd_power_unref on EVERY path after this call!',
    'snd_power_unref': '🔻 PUT: atomic_dec(&card->power_ref). Always runs.',
    'reset_control_deassert': '🔺 GET: increments deassert_count.',
    'reset_control_assert': '🔻 PUT: decrements deassert_count.',
    'chcr_inc_wrcount': '🔺 GET: CONDITIONAL. Only incs dev->inflight if dev->state!=CHCR_DETACH(return 0). Returns 1=skip.',
    'chcr_dec_wrcount': '🔻 PUT: atomic_dec(&dev->inflight). Always runs.',
    'iwpm_get_nlmsg_request': '🔺 GET: kref_init+kref_get→refcount=1. Returns object. Caller must release.',
    'iwpm_free_nlmsg_request': '🔻 PUT: kref_put callback. Releases when refcount→0.',
    'kref_init': '🔺 INIT: sets refcount to 1 (absolute). NOT a get from external reference.',
    'kref_get': '🔺 GET: unconditional refcount_inc. Always +1.',
    'kref_get_unless_zero': '🔺 GET: CONDITIONAL. Only incs if refcount>0. Returns true=success, false=not inc\'d.',
    'kref_put': '🔻 PUT: refcount_dec_and_test. Releases when→0.',
    'atomic_inc': '🔺 GET: unconditional +1.',
    'atomic_dec': '🔻 PUT: unconditional -1.',
    'refcount_inc': '🔺 GET: unconditional +1.',
    'refcount_dec': '🔻 PUT: unconditional -1.',
    'refcount_dec_and_test': '🔻 PUT: -1, returns true if→0.',
    'of_node_get': '🔺 GET: kobject_get on node. Caller must of_node_put.',
    'of_node_put': '🔻 PUT: kobject_put on node.',
    'get_device': '🔺 GET: kobject_get on dev.',
    'put_device': '🔻 PUT: kobject_put on dev.',
    'dma_fence_get': '🔺 GET: kref_get on fence.',
    'dma_fence_put': '🔻 PUT: kref_put on fence.',
    'power_supply_get_by_name': '🔺 GET: CONDITIONAL. Returns PSU with ref held, or NULL.',
    'power_supply_put': '🔻 PUT: put_device on PSU.',
    'ihold': '🔺 GET: unconditional +1 on inode.',
    'iput': '🔻 PUT: -1 on inode.',
    'get_pid': '🔺 GET: refcount_inc on pid.',
    'put_pid': '🔻 PUT: refcount_dec on pid.',
    'clk_get': '🔺 GET: CONDITIONAL. Returns clk with ref, or ERR_PTR.',
    'clk_put': '🔻 PUT: releases clk ref.',
    'pci_get_device': '🔺 GET: CONDITIONAL. Returns pci_dev with ref, or NULL.',
    'pci_dev_put': '🔻 PUT: put_device on pci_dev.',
    'dev_get_by_index': '🔺 GET: CONDITIONAL. Returns net_device with ref, or NULL.',
    'dev_put': '🔻 PUT: releases net_device ref.',
    'nvmet_cq_get': '🔺 GET: kref_get_unless_zero. CONDITIONAL.',
    'nvmet_cq_put': '🔻 PUT: kref_put.',
    'mlxsw_sp_lag_get': '🔺 GET: refcount_inc.',
    'mlxsw_sp_lag_put': '🔻 PUT: refcount_dec_and_test.',
    'taprio_offload_get': '🔺 GET: refcount_inc.',
    'taprio_offload_free': '🔻 PUT: refcount_dec_and_test.',
    'gntdev_alloc_map': '🔺 GET: kref_init→refcount=1.',
    'gntdev_put_map': '🔻 PUT: refcount_dec_and_test.',
    'sctp_auth_shkey_create': '🔺 GET: alloc+init refcount.',
    'sctp_auth_shkey_release': '🔻 PUT: kref_put.',
    'sctp_auth_key_put': '🔻 PUT: refcount_dec_and_test.',
    'host1x_job_alloc': '🔺 GET: alloc+init refcount.',
    'host1x_job_put': '🔻 PUT: kref_put.',
    'eventfd_ctx_fdget': '🔺 GET: CONDITIONAL. Returns eventfd_ctx with ref, or ERR_PTR.',
    'eventfd_ctx_put': '🔻 PUT: kref_put.',
    'acquire_ipmi_user': '🔺 GET: kref_get. CONDITIONAL (returns NULL on fail).',
    'release_ipmi_user': '🔻 PUT: kref_put.',
    'qrtr_node_lookup': '🔺 GET: CONDITIONAL. Returns node with ref, or NULL.',
    'qrtr_node_release': '🔻 PUT: kref_put.',
}


def parse_warning(line: str) -> dict | None:
    for pat, types in [
        (r'(?:\d+:)?([^:]+):(\d+)\s+(\S+)\(\)\s+warn:\s+(refcount leak|inconsistent refcounting|refcount excess put)\s+\'([^\']+)\'(?::\s+lines=\'([^\']*)\')?',
         ['file','line','func','warn','counter','lines']),
        (r'(?:\d+:)?([^:]+):(\d+)\s+(\S+)\(\)\s+(error|warn):\s+(using|passing|dereferencing|returning)\s+\'([^\']+)\'\s+after\s+(?:possible\s+)?refcount release\s*\(line\s+(\d+)\)',
         ['file','line','func','severity','action','var','release_line']),
    ]:
        m = re.match(pat, line.strip())
        if m:
            d = {pat: m.group(i+1) for i, pat in enumerate(types)}
            d['_raw'] = line.strip()
            if 'line' in d: d['line'] = int(d['line'])
            return d
    return None


def extract_inc_dec_fns(line: str) -> tuple:
    incs, decs = [], []
    m = re.search(r'inc:\[([^\]]*)\]', line)
    if m: incs = [x.strip() for x in m.group(1).split(',') if x.strip()]
    m = re.search(r'dec:\[([^\]]*)\]', line)
    if m: decs = [x.strip() for x in m.group(1).split(',') if x.strip()]
    return incs, decs


def get_contract(fn_name: str, func_dir: str) -> str | None:
    """获取函数契约: 合并已知库 + 函数报告的 contract_summary"""
    base = KNOWN_CONTRACTS.get(fn_name)
    jpath = os.path.join(func_dir, f"{fn_name}.json")
    cs_from_json = ''
    extra_info = []
    if os.path.exists(jpath):
        try:
            with open(jpath) as f:
                d = json.load(f)
            purity = d.get('final', {}).get('purity', d.get('purity', '?'))
            wrapper = d.get('final', {}).get('is_wrapper', False)
            cond = d.get('final', {}).get('conditionality', '?')
            cs = d.get('final', {}).get('contract_summary', '')
            callees = d.get('callee_func_info_list', [])
            gops = ','.join(f"{c.get('callee_function_name','?')}({c.get('get_or_put','?')})" for c in callees[:3])
            if purity and purity != '?': extra_info.append(f"purity={purity}")
            if wrapper: extra_info.append("wrapper")
            if 'condition' in cond: extra_info.append(cond)
            if gops: extra_info.append(f"→{gops}")
            if cs: cs_from_json = cs.strip()
        except: pass

    if base:
        # Merge: base contract + JSON contract_summary if available
        if cs_from_json and cs_from_json not in base:
            return f"{base} 📋 {cs_from_json}"
        if extra_info:
            return f"{base} ({'; '.join(extra_info)})"
        return base

    if extra_info or cs_from_json:
        parts = list(extra_info)
        if cs_from_json: parts.append(cs_from_json[:200])
        return '; '.join(parts)

    return None


def find_function_source(filepath: str, func_name: str) -> tuple | None:
    lines = []
    if os.path.exists(filepath):
        with open(filepath, encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    if not lines: return None
    for i, ln in enumerate(lines):
        # Check if this line contains the function definition
        if re.search(rf'\b{re.escape(func_name)}\s*\(', ln):
            # Verify it's a definition, not a call: should be at file scope
            stripped = ln.strip()
            is_def = (
                re.match(rf'^(?:static\s+|inline\s+|__\w+\s+|const\s+)*(?:struct\s+|enum\s+|union\s+)?[\w\s\*]+\s*{re.escape(func_name)}\s*\(', stripped) or
                re.match(rf'^{re.escape(func_name)}\s*\(', stripped)
            )
            if is_def:
                out = []; depth = 0; started = False
                for ii in range(i, min(len(lines), i + 800)):
                    ln2 = lines[ii]; out.append(f"{ii+1}: {ln2.rstrip()}")
                    if not started:
                        if '{' in ln2: started = True; depth += ln2.count('{') - ln2.count('}')
                    else:
                        depth += ln2.count('{') - ln2.count('}')
                        if depth <= 0: break
                return '\n'.join(out), i + 1
    return None


def prepare_context(w: dict, func_dir: str, kernel_dir: str) -> str:
    """构建极简审计上下文"""
    lines = []
    # Handle both old field names (function/warn_type/counter_path/get_lines)
    # and new field names (func/warn/counter/lines/file/line/var)
    fn = w.get('function') or w.get('func') or '?'
    wt = w.get('warn_type') or w.get('warn') or w.get('severity') or '?'
    cp = w.get('counter_path') or w.get('counter') or w.get('var') or '?'
    gl = w.get('get_lines') or w.get('lines') or w.get('release_line') or ''
    fpath = w.get('file') or '?'
    fline = w.get('line') or 0

    lines.append(f"# Audit: {fpath}:{fline} {fn}()")
    lines.append("")
    lines.append(f"**Warning**: `{wt}` on `{cp}`")
    lines.append(f"**Line**: `{fpath}:{fline}`")

    # Counter type analysis
    cp_lower = cp.lower()
    counter_hints = []
    if 'deassert_count' in cp_lower:
        counter_hints.append("⚠️ deassert_count = reset_control internal counter. IS a real refcount — deassert/assert MUST balance")
    if 'power.usage_count' in cp_lower:
        counter_hints.append("⚠️ pm_runtime usage_count. Probe error paths MUST release with pm_runtime_put_sync")
    if 'kref.refcount' in cp_lower or 'refcount.refs' in cp_lower:
        counter_hints.append("Standard kref — MUST kref_put on all paths")
    if 'inflight' in cp_lower or 'wrcount' in cp_lower:
        counter_hints.append("⚡ inflight counter — async completion only covers SUCCESSFULLY submitted ops")

    if gl:
        lines.append(f"**GET at lines**: `{gl}` — these are where the refcount was acquired")
    else:
        lines.append(f"**GET at lines**: (uncertain — 'inconsistent' warnings don't specify exact get location)")

    if counter_hints:
        lines.append(f"**Counter context**: {'; '.join(counter_hints)}")
    lines.append("")

    # 从原始行提取 inc/dec 函数
    raw = w.get('_raw', '')
    incs, decs = extract_inc_dec_fns(raw)
    if incs or decs:
        lines.append("## 🔴 Get/Put Contracts (MUST READ)")
        lines.append("")
        for fname in incs:
            c = get_contract(fname, func_dir)
            if c: lines.append(f"- **GET** `{fname}()`: {c}")
            else: lines.append(f"- **GET** `{fname}()`: (unknown — use [NEED_SOURCE] to investigate)")
        for fname in decs:
            c = get_contract(fname, func_dir)
            if c: lines.append(f"- **PUT** `{fname}()`: {c}")
            else: lines.append(f"- **PUT** `{fname}()`: (unknown — use [NEED_SOURCE] to investigate)")
        lines.append("")

        # Unconditional GETs warning
        unconditional_gets = []
        for fname in incs:
            c = get_contract(fname, func_dir)
            if c and ('UNCONDITIONAL' in c.upper() or 'unconditional' in c.lower()):
                unconditional_gets.append(fname)
        if unconditional_gets:
            lines.append(f"🔴 **UNCONDITIONAL GETs**: `{'`, `'.join(unconditional_gets)}` — these ALWAYS increment. Error returns after these calls MUST put!")
            lines.append("")

        # GET lines hint for inconsistent warnings
        if not gl:
            lines.append(f"💡 **Look for GET calls**: `{'`, `'.join(incs[:3])}` in the source — these are the GET operations smatch tracked.")
            lines.append("")

    # 主函数源码: cscope 优先
    src_done = False
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from accurate_func_locator import AccurateFuncLocator
        locator = AccurateFuncLocator(kernel_dir)
        if locator.cscope_db_exists():
            r = locator.find_function_source(fn)
            if r and r.get('source_code'):
                lines.append(f"## Main Function: `{fn}()` ({r.get('file', fpath)}, line {r.get('start_line', 1)})")
                lines.append("")
                lines.append("```c")
                lines.append(r['source_code'])
                lines.append("```")
                lines.append("")
                src_done = True
    except: pass

    if not src_done:
        # Fallback: file-based regex
        filepath = os.path.join(kernel_dir, fpath)
        if not os.path.exists(filepath):
            filepath = os.path.normpath(filepath)
        if os.path.exists(filepath):
            fs = find_function_source(filepath, fn)
            if fs:
                fsource, fstart = fs
                lines.append(f"## Main Function: `{fn}()` ({fpath}, line {fstart})")
                lines.append("")
                lines.append("```c")
                lines.append(fsource)
                lines.append("```")
                lines.append("")
                src_done = True

    if not src_done:
        lines.append(f"## Main Function: `{fn}()` — SOURCE NOT FOUND, use [NEED_SOURCE] {fn}")
        lines.append("")

    # 审计指引
    lines.append("## Instructions")
    lines.append("")
    lines.append("1. **READ the contracts above** — they tell you exactly what each get/put does")
    lines.append("2. **Enumerate ALL return paths** in the main function")
    lines.append("3. **For each return path**: was GET executed? Was PUT executed?")
    lines.append("4. **Use `[NEED_SOURCE] function_name`** to request ANY callee source you need")
    lines.append("5. **Check**: IS_ERR guard? ownership transfer? devm cleanup? async deferral?")
    lines.append("6. Output: `## VERDICT: {REAL_BUG | FALSE_POSITIVE}` with confidence")
    lines.append("")

    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description='s9_v3: Minimal contract-based audit context')
    p.add_argument('--warns', required=True)
    p.add_argument('--func-dir', default=DEFAULT_FUNC_DIR)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--kernel-dir', default=KERNEL_DIR)
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()

    warnings = []
    with open(args.warns) as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith('#'): continue
            w = parse_warning(ln)
            if w: warnings.append(w)

    if args.limit > 0: warnings = warnings[:args.limit]
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Preparing {len(warnings)} contexts...")
    for i, w in enumerate(warnings):
        ctx = prepare_context(w, args.func_dir, args.kernel_dir)
        fn = w.get('function') or w.get('func') or 'unknown'
        fp = w.get('file') or '?'
        ln = w.get('line') or 0
        safe = f"{fp.replace('/','_')}_{ln}_{fn}"
        out = os.path.join(args.output_dir, f"{i+1:04d}_{safe}.md")
        with open(out, 'w') as f: f.write(ctx)
        incs, decs = extract_inc_dec_fns(w.get('_raw', ''))
        n_contracts = sum(1 for fname in incs+decs if get_contract(fname, args.func_dir))
        print(f"  [{i+1}] {fn}() — {len(incs)}G/{len(decs)}P, {n_contracts} contracts")

    print(f"Done: {args.output_dir}/")

if __name__ == '__main__':
    main()
