#!/usr/bin/env python3
"""
s9_prepare_audit_context.py — 为 smatch refcount 告警准备审计上下文

v2: 复用 s1 的 AccurateFuncLocator (cscope) 进行精确函数定位。
    提供完整函数体 + get-site 附近代码 + 候选被调用方列表。

Usage:
    python3 s9_prepare_audit_context.py -w "FILE:LINE FUNC() warn: ..."
    python3 s9_prepare_audit_context.py --input warns.txt [--limit N]
"""

import argparse, json, os, re, subprocess, sys

KERNEL_DIR = os.environ.get("REFCOUNT_KERNEL_DIR", "")

# ---------------------------------------------------------------------------
# 复用 s1 的 AccurateFuncLocator (cscope)
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from accurate_func_locator import AccurateFuncLocator
    _USE_CSCOPE = True
except ImportError:
    _USE_CSCOPE = False


def parse_warning(line: str) -> dict:
    m = re.match(
        r'(?:\d+:)?([^:]+):(\d+)\s+(\S+)\(\)\s+warn:\s+'
        r'(refcount leak|inconsistent refcounting)\s+\'([^\']+)\''
        r'(?::\s+lines=\'([^\']*)\')?', line.strip())
    if not m: return None
    return {"file": m.group(1), "line": int(m.group(2)),
            "function": m.group(3), "warn_type": m.group(4),
            "counter_path": m.group(5), "get_lines": m.group(6) or ""}


def read_file_lines(filepath: str):
    if not os.path.exists(filepath): return []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


_CSCOPE_LOCATOR = None  # 单例缓存

def get_func_source_cscope(func_name: str, kernel_dir: str) -> tuple:
    """使用 s1 的 AccurateFuncLocator (cscope) 精确查找函数"""
    global _CSCOPE_LOCATOR
    if not _USE_CSCOPE:
        return (None, None)
    try:
        if _CSCOPE_LOCATOR is None:
            _CSCOPE_LOCATOR = AccurateFuncLocator(kernel_dir)
            if not _CSCOPE_LOCATOR.cscope_db_exists():
                return (None, None)  # cscope DB not built, skip
        result = _CSCOPE_LOCATOR.find_function_source(func_name)
        if result and result.get("confidence") in ("high", "medium"):
            src = result.get("source_code", "")
            start = result.get("start_line", 1)
            return (src, start)
    except Exception:
        pass
    return (None, None)


def get_func_source_grep(filepath: str, func_name: str) -> tuple:
    """grep 回退方案"""
    lines = read_file_lines(filepath)
    if not lines: return (None, None)
    for pattern in [rf'^{func_name}\s*\(', rf'^(?:static\s+|inline\s+|__\w+\s+)*[\w\s\*]+\s+{func_name}\s*\(']:
        for i, ln in enumerate(lines):
            if re.match(pattern, ln):
                out = []; depth = 0; started = False
                for ii in range(i, min(len(lines), i + 600)):
                    ln2 = lines[ii]; out.append(f"{ii+1}: {ln2.rstrip()}")
                    if not started:
                        if "{" in ln2: started = True; depth += ln2.count("{") - ln2.count("}")
                    else:
                        depth += ln2.count("{") - ln2.count("}")
                        if depth <= 0: break
                return ("\n".join(out), i + 1)
    return (None, None)


def get_context_around(lines: list, target_lines: list, window: int = 8) -> str:
    """提取目标行附近的代码窗口"""
    ctx = set()
    for gl in target_lines:
        for li in range(max(0, gl - window), min(len(lines), gl + window + 1)):
            ctx.add(li)
    if not ctx: return ""
    out = []
    prev = -2
    for li in sorted(ctx):
        if li > prev + 1:
            out.append(f"  ...")
        out.append(f"{li+1}: {lines[li].rstrip()}")
        prev = li
    return "\n".join(out)


def find_callee_functions_near(lines: list, target_line: int, radius: int = 30) -> list:
    """在告警行附近查找可能的被调用函数"""
    skip = {'if','while','for','switch','return','sizeof','typeof','BUG_ON','WARN_ON',
            'likely','unlikely','IS_ERR','PTR_ERR','ERR_PTR','container_of',
            'list_for_each','rcu_read','int','void','char','struct','unsigned',
            'long','static','const','goto','break','continue','case','default',
            'printk','pr_debug','pr_info','pr_err','pr_warn','dev_err','dev_dbg',
            'set_state','get_state','__','READ_ONCE','WRITE_ONCE','smp_','barrier',
            'mutex_','spin_','kfree','kmalloc','kzalloc','memset','memcpy'}
    seen = set()
    for i in range(max(0, target_line - radius), min(len(lines), target_line + radius)):
        for m in re.finditer(r'\b(\w+)\s*\(', lines[i]):
            fn = m.group(1)
            if fn not in skip and fn not in seen:
                seen.add(fn)
    return sorted(seen)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--warning")
    parser.add_argument("--input")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--kernel-dir", default=KERNEL_DIR)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if args.output_dir is None:
        if args.input:
            args.output_dir = os.path.join(os.path.dirname(os.path.abspath(args.input)) or ".", "audit_contexts")
        else:
            args.output_dir = "audit_contexts"

    warnings = []
    if args.warning:
        p = parse_warning(args.warning)
        if p: warnings.append(p)
    elif args.input:
        with open(args.input) as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#"): continue
                p = parse_warning(ln)
                if p: warnings.append(p)
    if not warnings:
        print("No warnings."); sys.exit(1)
    if args.limit > 0: warnings = warnings[:args.limit]

    os.makedirs(args.output_dir, exist_ok=True)

    for i, w in enumerate(warnings):
        filepath = os.path.join(args.kernel_dir, w["file"])
        safe = f"{w['file'].replace('/','_')}_{w['line']}_{w['function']}"
        out_file = os.path.join(args.output_dir, f"{i+1:04d}_{safe}.md")

        # --- Step 1: 主函数源码 (cscope + grep fallback) ---
        fsource, fstart = (None, None)
        if _USE_CSCOPE:
            fsource, fstart = get_func_source_cscope(w["function"], args.kernel_dir)
        if not fsource:
            fsource, fstart = get_func_source_grep(filepath, w["function"])

        if not fsource:
            print(f"  WARN: Cannot find {w['function']}() in {w['file']}")
            continue

        # --- Step 2: get-site 上下文 ---
        all_lines = read_file_lines(filepath)
        get_ctx = ""
        glines = []
        if w["get_lines"]:
            glines = [int(x) for x in w["get_lines"].split(",") if x.strip().isdigit()]
        if glines:
            get_ctx = get_context_around(all_lines, glines)

        # --- Step 3: 候选被调用方 ---
        target_line = w["line"]
        if glines:
            target_line = glines[0]  # prefer get-site for callee search
        callees = find_callee_functions_near(all_lines, target_line)

        # --- Build output ---
        ctx = []
        ctx.append(f"# Audit: {w['file']}:{w['line']} {w['function']}()")
        ctx.append("")
        ctx.append("## Warning Info")
        ctx.append("```")
        ctx.append(f"File:         {w['file']}:{w['line']}")
        ctx.append(f"Function:     {w['function']}()")
        ctx.append(f"Warn Type:    {w['warn_type']}")
        ctx.append(f"Counter Path: {w['counter_path']}")
        ctx.append(f"Get at lines: {w['get_lines']}")
        ctx.append("```")
        ctx.append("")
        ctx.append(f"## Main Function Source ({w['file']}, ~{fsource.count(chr(10))} lines)")
        ctx.append(f"_Function body begins near line {fstart}_")
        ctx.append("")
        ctx.append(f"```c")
        ctx.append(fsource)
        ctx.append(f"```")

        if get_ctx:
            ctx.append("")
            ctx.append(f"## Get-Site Context (±8 lines around lines={w['get_lines']})")
            ctx.append("")
            ctx.append("```c")
            ctx.append(get_ctx)
            ctx.append("```")

        if callees:
            # Filter to most likely refcount-related
            refcount_hints = [c for c in callees if
                any(kw in c.lower() for kw in ['refcount','kref','atomic','get','put','acquire','release','inc','dec'])]
            if refcount_hints:
                ctx.append("")
                ctx.append("## Potential Refcount-Related Callees")
                ctx.append("_Functions called near the warning site that may be relevant_")
                for c in refcount_hints:
                    ctx.append(f"- `{c}()`")
            ctx.append("")
            ctx.append("## Nearby Functions (not exhaustive)")
            ctx.append("_Functions called within ±30 lines of the warning site. The agent may use [NEED_SOURCE] for functions not listed here._")
            ctx.append(", ".join(f"`{c}()`" for c in callees[:40]))

        with open(out_file, "w") as f:
            f.write("\n".join(ctx))

        n_callees = len(callees)
        n_hints = len(refcount_hints) if 'refcount_hints' in dir() else 0
        print(f"  [{i+1}] {w['file']}:{w['line']} {w['function']}() "
              f"({fsource.count(chr(10))} lines, {n_hints}/{n_callees} callees)"
              f" → {os.path.basename(out_file)}")

    print(f"Prepared {len(warnings)} contexts in {args.output_dir}/")
    print(f"cscope: {'available' if _USE_CSCOPE else 'FALLBACK (install cscope for better results)'}")


if __name__ == "__main__":
    main()
