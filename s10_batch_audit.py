#!/usr/bin/env python3
"""
s10_v3_batch_audit.py — 契约驱动批量审计 (API + 多线程)

使用 s9_v3 的极简契约上下文 + template_audit_v3 进行审计。
每个上下文包含: warning + 合约 + 主函数源码
API 单轮判断, 多线程并行。

Usage:
    python3 s10_v3_batch_audit.py \
        --input-dir /tmp/contract_contexts \
        --api --workers 16 \
        --output audit_report_v3.md
"""

import argparse, json, os, re, sys, time, threading
import concurrent.futures
import urllib.request, urllib.error
from collections import defaultdict

KERNEL_DIR = os.environ.get("REFCOUNT_KERNEL_DIR", "")
MAX_ROUNDS = 3

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_config.env")
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template_audit_v3.md")

def load_config():
    cfg = {
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "api_url": os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages"),
        "model": os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
        "max_tokens": 32768
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line: continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "ANTHROPIC_API_KEY": cfg["api_key"] = v
                elif k == "ANTHROPIC_API_URL": cfg["api_url"] = v
                elif k == "ANTHROPIC_MODEL": cfg["model"] = v
    return cfg

class APIClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self._openai = "chat/completions" in cfg["api_url"]

    def chat(self, system: str, user: str, history: list = None) -> str:
        for attempt in range(3):
            try:
                body = {"model": self.cfg["model"], "max_tokens": self.cfg["max_tokens"], "messages": []}
                if self._openai:
                    if system: body["messages"].append({"role": "system", "content": system})
                    if history: body["messages"].extend(history)
                    body["messages"].append({"role": "user", "content": user})
                else:
                    if system: body["system"] = system
                    msgs = []
                    if history: msgs.extend(history)
                    msgs.append({"role": "user", "content": user})
                    body["messages"] = msgs

                data = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(self.cfg["api_url"], data=data)
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {self.cfg['api_key']}")
                if not self._openai:
                    req.add_header("anthropic-version", "2023-06-01")

                with urllib.request.urlopen(req, timeout=300) as resp:
                    r = json.loads(resp.read().decode("utf-8"))
                    if "content" in r and isinstance(r["content"], list):
                        for block in r["content"]:
                            if block.get("type") == "text": return block["text"]
                    if "choices" in r:
                        return r["choices"][0]["message"]["content"]
                    return str(r)
            except urllib.error.HTTPError as e:
                if e.code == 429: time.sleep(2 ** attempt); continue
                if e.code >= 500: time.sleep(1 + attempt); continue
                return f"API_ERR {e.code}"
            except Exception as e:
                if attempt < 2: time.sleep(1 + attempt); continue
                return f"API_ERR {str(e)[:100]}"
        return "API_ERR max retries"

def parse_verdict(text: str) -> dict:
    r = {"verdict": "UNCLEAR", "confidence": "?", "api_error": False}

    # Check for API errors first
    if text.startswith("API_ERR"):
        r["api_error"] = True
        return r

    # Check for truncation: does the response have a verdict?
    has_verdict = False

    # Broad patterns for VERDICT
    for pat in [
        r'VERDICT\s*:?\s*REAL[\s_]*BUG',
        r'VERDICT\s*:?\s*FALSE[\s_]*POSITIVE',
        r'\*\*VERDICT\*\*\s*:?\s*REAL[\s_]*BUG',
        r'\*\*VERDICT\*\*\s*:?\s*FALSE[\s_]*POSITIVE',
        r'##\s*VERDICT\s*:?\s*REAL[\s_]*BUG',
        r'##\s*VERDICT\s*:?\s*FALSE[\s_]*POSITIVE',
        # Also match at end of line
        r'(?m)^VERDICT:\s*(REAL[_ ]BUG|FALSE[_ ]POSITIVE)',
        r'(?m)^\*\*VERDICT\*\*:\s*(REAL[_ ]BUG|FALSE[_ ]POSITIVE)',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            r["verdict"] = "REAL BUG" if "REAL" in m.group().upper() else "FALSE POSITIVE"
            has_verdict = True
            break

    # Fallback: check if response contains strong BUG/LEAK language
    if not has_verdict:
        bug_signals = re.findall(r'(?:REAL[\s_]*BUG|LEAK|MISSING[\s_]*PUT|missing[\s_]*put)', text, re.I)
        fp_signals = re.findall(r'(?:FALSE[\s_]*POSITIVE|BALANCED|all paths.*put|no leak)', text, re.I)
        if len(bug_signals) > len(fp_signals):
            r["verdict"] = "REAL BUG"; r["confidence"] = "LOW"
        elif fp_signals:
            r["verdict"] = "FALSE POSITIVE"; r["confidence"] = "LOW"

    for pat in [r'CONFIDENCE\s*:?\s*(HIGH|MEDIUM|LOW)', r'\*\*Confidence\*\*\s*:?\s*(HIGH|MEDIUM|LOW)']:
        m = re.search(pat, text, re.I)
        if m: r["confidence"] = m.group(1).strip().upper(); break

    # Extract reasoning: take meaningful text before VERDICT
    verdict_pos = text.find("VERDICT")
    if verdict_pos > 0:
        reasoning_text = text[max(0, verdict_pos-300):verdict_pos]
    else:
        reasoning_text = text[-500:]
    # Find a meaningful sentence
    for line in reasoning_text.split('\n'):
        line = line.strip()
        if len(line) > 20 and any(kw in line.lower() for kw in ['return', 'leak', 'put', 'get', 'path', 'line', 'bug', 'fp', 'goto', 'error', 'missing']):
            r["reasoning"] = line[:300]
    if not r.get("reasoning"):
        r["reasoning"] = reasoning_text.strip()[-200:]
    return r

def has_info_request(text: str) -> list:
    """Check if LLM requests source code. Returns list of function names."""
    requests = set()
    for m in re.finditer(r'\[NEED_SOURCE\]\s+(\w+)', text):
        requests.add(m.group(1))
    return list(requests)

def fetch_source(func_name: str) -> str:
    """Find function source code using grep + cscope fallback"""
    import subprocess
    # Try to find in common kernel directories
    dirs = ["include", "kernel", "fs", "drivers", "net", "mm", "block", "crypto", "security", "sound", "lib", "arch"]
    for d in dirs:
        try:
            r = subprocess.run(
                ["grep", "-rnEl", f"^{func_name}\\s*\\(",
                 os.path.join(KERNEL_DIR, d)],
                capture_output=True, text=True, timeout=10)
            if r.stdout.strip():
                fpath = r.stdout.strip().split('\n')[0]
                if fpath:
                    with open(fpath, errors='ignore') as f:
                        lines = f.readlines()
                    # Find function definition
                    for i, ln in enumerate(lines):
                        if re.match(rf'^(?:static\s+|inline\s+|__\w+\s+|const\s+)*\S+\s+{re.escape(func_name)}\s*\(', ln) or \
                           re.match(rf'^{re.escape(func_name)}\s*\(', ln):
                            out = []; depth = 0; started = False
                            for ii in range(i, min(len(lines), i + 500)):
                                ln2 = lines[ii]; out.append(f"{ii+1}: {ln2.rstrip()}")
                                if not started:
                                    if '{' in ln2: started = True; depth += ln2.count('{') - ln2.count('}')
                                else:
                                    depth += ln2.count('{') - ln2.count('}')
                                    if depth <= 0: break
                            return f"// {fpath}\n" + '\n'.join(out)
        except: pass
    return f"// SOURCE NOT FOUND for {func_name}"

def audit_one(context_file: str, template: str, cfg: dict) -> dict:
    with open(context_file) as f: context = f.read()

    # Extract warning info
    wm = re.search(r'# Audit:\s+(\S+):(\d+)\s+(\S+)\(\)', context)
    tm = re.search(r'\*\*Warning\*\*:\s*`(.+?)`\s+on\s+`(.+?)`', context)
    fname = wm.group(1) if wm else "?"
    fline = int(wm.group(2)) if wm else 0
    func = wm.group(3) if wm else "?"
    wtype = tm.group(1) if tm else "?"
    cpath = tm.group(2) if tm else "?"

    system = template if template else "You audit kernel refcount bugs."
    user_msg = (
        f"{context}\n\n---\n"
        f"## Audit Task\n"
        f"Analyze `{func}()` above. READ contracts first, then enumerate ALL return paths.\n\n"
        "Your response MUST start with the path table, then end with:\n"
        "VERDICT: REAL_BUG  (or VERDICT: FALSE_POSITIVE)\n"
        "CONFIDENCE: HIGH  (or MEDIUM / LOW)\n"
    )

    client = APIClient(cfg)
    resp = client.chat(system, user_msg)

    # Up to 2 rounds of [NEED_SOURCE]
    history = []
    for need_round in range(2):
        requests = has_info_request(resp)
        if not requests or resp.startswith("API_ERR"):
            break
        sources = []
        for fn in requests[:3]:
            src = fetch_source(fn)
            if src and 'SOURCE NOT FOUND' not in src:
                sources.append(f"```c\n// {fn}()\n{src}\n```")
        if not sources:
            break
        history.append({"role": "assistant", "content": resp})
        followup = (
            f"[SYSTEM] Source for requested functions (round {need_round+1}/2):\n\n"
            f"{chr(10).join(sources)}\n\n"
            f"Continue analysis. Request more with [NEED_SOURCE] or output VERDICT."
        )
        history.append({"role": "user", "content": followup})
        resp2 = client.chat(system, followup,
                          [h for h in history[:-1]] if len(history) > 1 else None)
        if resp2 and not resp2.startswith("API_ERR"):
            resp = resp + f"\n\n--- [NEED_SOURCE r{need_round+1}] ---\n\n" + resp2

    parsed = parse_verdict(resp)

    return {
        "file": fname, "line": fline, "function": func,
        "warn_type": wtype, "counter": cpath,
        "verdict": parsed.get("verdict", "UNCLEAR"), "confidence": parsed.get("confidence", "?"),
        "reasoning": parsed.get("reasoning", ""),
        "full_response": resp,
        "rounds": 2 if requests else 1,
    }

def run_batch(input_dir: str, output_file: str, limit: int, workers: int, cfg: dict, results_dir: str = None):
    template = ""
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE) as f: template = f.read()

    ctx_files = sorted([f for f in os.listdir(input_dir)
                        if f.endswith('.md') and not f.startswith('_') and not f.startswith('detail_')])

    # Skip already-processed files (check results_dir for existing detail files)
    if results_dir:
        os.makedirs(results_dir, exist_ok=True)
        existing = set(os.listdir(results_dir))
        skipped = 0
        pending = []
        for cf in ctx_files:
            # Context files: NNNN_filepath_line_func.md
            # Detail files: PREFIX_filepath_line_func.md
            # Match by stripping the context's NNNN_ prefix
            parts = cf.split('_', 1)
            suffix = parts[1] if len(parts) > 1 else cf
            if any(suffix in d for d in existing):
                skipped += 1
            else:
                pending.append(cf)
        if skipped > 0:
            print(f"Skipping {skipped} already-audited files")
        ctx_files = pending

    if limit > 0: ctx_files = ctx_files[:limit]

    print(f"Auditing {len(ctx_files)} files with {workers} workers\n")

    results_lock = threading.Lock()
    results = []
    done = [0]; t0 = time.time()

    def worker(cf):
        r = audit_one(os.path.join(input_dir, cf), template, cfg)
        with results_lock:
            results.append(r); done[0] += 1
            n = done[0]; elapsed = time.time() - t0
            rate = n / elapsed if elapsed > 0 else 0
            eta = (len(ctx_files) - n) / rate if rate > 0 else 0
            icon = '🐛' if 'REAL BUG' in r['verdict'] else ('✅' if 'FALSE' in r['verdict'] else '❓')
            print(f"  [{n}/{len(ctx_files)}] {icon} {r['function']}() → {r['verdict']} ({r['confidence']}) | {rate:.1f}/s ETA:{eta:.0f}s")

            # Write individual detail file
            if results_dir:
                safe = f"{r['file'].replace('/','_')}_{r['line']}_{r['function']}"
                prefix = {'REAL BUG': 'BUG', 'FALSE POSITIVE': 'FP', 'UNCLEAR': 'UN'}.get(r['verdict'], 'UN')
                dfile = os.path.join(results_dir, f"{prefix}_{safe}.md")
                try:
                    with open(dfile, 'w') as df:
                        df.write(f"# {r['verdict']}: {r['file']}:{r['line']} {r['function']}()\n\n")
                        df.write(f"**Confidence**: {r['confidence']} | **Counter**: `{r['counter']}`\n\n")
                        df.write(f"## Reasoning\n\n{r.get('reasoning','')}\n\n")
                        df.write(f"## Full Response\n\n```\n{r['full_response'][:3000]}\n```\n")
                except: pass

            # Checkpoint every 500
            if n % 500 == 0 and results_dir:
                bugs = sum(1 for x in results if 'REAL BUG' in x['verdict'])
                fps = sum(1 for x in results if 'FALSE' in x['verdict'])
                unc = sum(1 for x in results if 'UNCLEAR' in x.get('verdict',''))
                # Use total detail count to avoid overwriting across batches
                total_done = n + skipped
                ckpt = os.path.join(results_dir, f"checkpoint_{total_done:06d}.md")
                with open(ckpt, 'w') as cf:
                    cf.write(f"# Checkpoint at {n}/{len(ctx_files)}\n\n")
                    cf.write(f"**Bugs**: {bugs} | **FP**: {fps} | **Unclear**: {unc}\n")
                    cf.write(f"**Rate**: {rate:.1f}/s | **Elapsed**: {elapsed:.0f}s\n")

        return r

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(worker, cf) for cf in ctx_files]
        concurrent.futures.wait(futures)

    elapsed = time.time() - t0
    _write_report(results, output_file, elapsed)

def _write_report(results, output_file, elapsed):
    real = [r for r in results if 'REAL BUG' in r['verdict']]
    fp = [r for r in results if 'FALSE' in r['verdict']]
    other = [r for r in results if r not in real and r not in fp]

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(f"# Interactive Audit Report (v3 contract-driven)\n\n")
        f.write(f"**Total**: {len(results)} | **Real Bugs**: {len(real)} | **FP**: {len(fp)} | **Other**: {len(other)}\n")
        f.write(f"**Time**: {elapsed:.0f}s\n\n")

        f.write("## Summary\n\n")
        f.write("| # | Function | File:Line | Verdict | Conf | Key Finding |\n")
        f.write("|---|----------|-----------|---------|------|-------------|\n")
        for i, r in enumerate(results):
            v_icon = '🐛' if 'REAL BUG' in r['verdict'] else ('✅' if 'FALSE' in r['verdict'] else '❓')
            f.write(f"| {i+1} | `{r['function']}()` | {r['file']}:{r['line']} | {v_icon} {r['verdict']} | {r['confidence']} | {r.get('reasoning','')[:100]} |\n")

        if real:
            f.write("\n## 🐛 Real Bugs Detail\n\n")
            for r in real:
                f.write(f"### {r['function']}() — {r['file']}:{r['line']}\n")
                f.write(f"**Confidence**: {r['confidence']} | **Counter**: `{r['counter']}`\n\n")
                f.write(f"{r.get('reasoning','')}\n\n")
                f.write(f"<details><summary>Full Response</summary>\n\n```\n{r['full_response'][:2000]}\n```\n</details>\n\n")

    print(f"\nReport: {output_file}")
    print(f"  🐛 Real Bugs: {len(real)} | ✅ FP: {len(fp)} | ❓ Other: {len(other)}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input-dir', required=True)
    p.add_argument('--output', default='audit_report_v3.md')
    p.add_argument('--api', action='store_true')
    p.add_argument('--workers', type=int, default=16)
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--results-dir', default=None, help='Directory for individual detail files + checkpoints')
    args = p.parse_args()

    if not args.api:
        print("Use --api to run API audit")
        return

    cfg = load_config()
    if not cfg["api_key"]:
        print("ERROR: No API key"); sys.exit(1)
    print(f"API: {cfg['api_url']} | Model: {cfg['model']}")
    run_batch(args.input_dir, args.output, args.limit, args.workers, cfg, args.results_dir)

if __name__ == '__main__':
    main()
