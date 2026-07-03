#!/usr/bin/env python3
"""
s10_v2_audit_agent.py — 多线程并行 refcount 告警审计引擎

v3 改进:
  1. 多线程并行 (ThreadPoolExecutor, I/O密集适合多线程)
  2. API 重试机制 (最多3次, 指数退避)
  3. 断点续传 (已完成的不重复审计)
  4. 实时进度 + 中间结果保存
  5. 每个线程独立 API client (线程安全)

Usage:
    python3 s10_v2_audit_agent.py --input-dir enriched_contexts/ --api --workers 8
    python3 s10_v2_audit_agent.py --input-dir enriched_contexts/ --api --workers 8 --limit 100
    python3 s10_v2_audit_agent.py --input-dir enriched_contexts/ --summary-only
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import threading
import concurrent.futures
from collections import defaultdict

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "template_audit_v2.md")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "api_config.env")

DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 300


def load_api_config(config_file: str = None) -> dict:
    if config_file is None:
        config_file = CONFIG_FILE
    cfg = {
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "api_url": os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages"),
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        "max_tokens": int(os.environ.get("AUDIT_MAX_TOKENS", "8192")),
    }
    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "ANTHROPIC_API_KEY":
                    cfg["api_key"] = v
                elif k == "ANTHROPIC_API_URL":
                    cfg["api_url"] = v
                elif k == "ANTHROPIC_MODEL":
                    cfg["model"] = v
                elif k == "AUDIT_MAX_TOKENS":
                    cfg["max_tokens"] = int(v)
    return cfg


# ---------------------------------------------------------------------------
# API 客户端 (每个线程独立实例)
# ---------------------------------------------------------------------------
class APIClient:
    def __init__(self, config: dict):
        self.api_key = config["api_key"]
        self.api_url = config["api_url"]
        self.model = config["model"]
        self.max_tokens = config.get("max_tokens", 8192)
        self._is_openai = "chat/completions" in self.api_url or "openai" in self.api_url.lower()
        self._lock = threading.Lock()  # 保护 send 操作

    def chat(self, messages: list, system: str = "") -> str:
        if self._is_openai:
            return self._chat_openai(messages, system)
        return self._chat_anthropic(messages, system)

    def _chat_anthropic(self, messages: list, system: str) -> str:
        body = {"model": self.model, "max_tokens": self.max_tokens, "messages": []}
        if system:
            body["system"] = system
        body["messages"] = messages
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=data)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("anthropic-version", "2023-06-01")
        return self._send(req)

    def _chat_openai(self, messages: list, system: str) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        body = {"model": self.model, "max_tokens": self.max_tokens, "messages": msgs}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=data)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        return self._send(req)

    def _send(self, req) -> str:
        last_error = ""
        for attempt in range(DEFAULT_MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    if "content" in result and isinstance(result["content"], list):
                        for block in result["content"]:
                            if block.get("type") == "text":
                                return block["text"]
                    if "choices" in result:
                        return result["choices"][0]["message"]["content"]
                    return str(result)
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}"
                if e.code == 429:  # Rate limit
                    time.sleep(2 ** attempt)
                    continue
                if e.code >= 500:  # Server error
                    time.sleep(1 + attempt)
                    continue
                body = e.read().decode("utf-8", errors="replace")
                return f"API ERROR {e.code}: {body[:500]}"
            except Exception as e:
                last_error = str(e)[:200]
                if attempt < DEFAULT_MAX_RETRIES - 1:
                    time.sleep(1 + attempt)
                    continue
        return f"API ERROR (after {DEFAULT_MAX_RETRIES} retries): {last_error}"


# ---------------------------------------------------------------------------
# Verdict 解析
# ---------------------------------------------------------------------------
def parse_verdict(response: str) -> dict:
    result = {
        "verdict": "UNCLEAR",
        "confidence": "?",
        "reasoning": "",
        "fp_pattern": "",
        "fix": "",
    }
    vm = re.search(r'(?:VERDICT|判定)[:\s]*[{\"\']?(REAL[_\s]BUG|FALSE[_\s]POSITIVE)',
                   response, re.IGNORECASE)
    if vm:
        result["verdict"] = vm.group(1).replace('_', ' ').strip()
    cm = re.search(r'(?:Confidence|CONFIDENCE|置信度)[:\s]*[{\"\']?(HIGH|MEDIUM|LOW)',
                   response, re.IGNORECASE)
    if cm:
        result["confidence"] = cm.group(1).strip()
    rm = re.search(r'(?:###\s*Reasoning|###\s*分析|##\s*Analysis)(.*?)(?:###|\Z)',
                   response, re.DOTALL | re.IGNORECASE)
    if rm:
        result["reasoning"] = rm.group(1).strip()[:500]
    fpm = re.search(r'(?:False Positive Pattern|误报模式)[:\s]*(.*?)(?:\n|$)',
                    response, re.IGNORECASE)
    if fpm:
        result["fp_pattern"] = fpm.group(1).strip()[:200]
    fm = re.search(r'(?:###\s*Fix|###\s*修复)(.*?)(?:###|\Z)',
                   response, re.DOTALL | re.IGNORECASE)
    if fm:
        result["fix"] = fm.group(1).strip()[:500]
    return result


# ---------------------------------------------------------------------------
# 审计引擎 (多线程版)
# ---------------------------------------------------------------------------
class AuditEngineV2:
    def __init__(self, template_file: str = None, api_config: dict = None):
        self.api_config = api_config or {}
        self.template = ""
        if template_file and os.path.exists(template_file):
            with open(template_file) as f:
                self.template = f.read()
        elif os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE) as f:
                self.template = f.read()

    def _make_client(self) -> APIClient:
        """每个线程创建独立的 API client"""
        return APIClient(self.api_config)

    def audit_single(self, context_file: str, allow_confirm: bool = False) -> dict:
        """单轮审计 (线程安全: 每次调用创建独立 client)"""
        with open(context_file) as f:
            context = f.read()

        # 从富化上下文中提取 warning 元信息 (支持两种格式)
        wm = re.search(r'(?:\*\*)?File(?:\*\*)?:\s+`?(\S+?)`?\s*\n.*?(?:\*\*)?Line(?:\*\*)?:\s+(\d+)',
                       context)
        if not wm:
            # Markdown 表格格式: | File | `path` | \n | Line | N |
            wm = re.search(r'\|\s*File\s*\|\s*`(\S+?)`\s*\|.*?\|\s*Line\s*\|\s*(\d+)\s*\|',
                           context)
        fm = re.search(r'(?:\*\*)?Function(?:\*\*)?:\s+`?(\S+)\(\)', context)
        if not fm:
            fm = re.search(r'\|\s*Function\s*\|\s*`(\S+)\(\)`\s*\|', context)
        am = re.search(r'Auto Classification[:\*\*\s]+(\S+)', context)

        # 从 title 行回退: # Audit #N: file:line func()
        title_m = re.search(r'#\s*Audit\s*#\d+:\s*(\S+):(\d+)\s+(\S+)\(\)', context)

        warning = {
            "file": wm.group(1) if wm else (title_m.group(1) if title_m else "?"),
            "line": int(wm.group(2)) if wm else (int(title_m.group(2)) if title_m else 0),
            "function": fm.group(1) if fm else (title_m.group(3) if title_m else "?"),
            "auto_class": am.group(1) if am else "NEEDS_REVIEW",
        }

        system_prompt = self.template if self.template else "You audit kernel refcount bugs."
        messages = [{
            "role": "user",
            "content": f"## Audit Task\n\n{context}\n\n---\n\n"
                       f"Based on the enriched context above, analyze this refcount warning "
                       f"and output your VERDICT. Remember: IS_ERR guards are NOT leaks, "
                       f"ownership transfer is NOT a leak. Check the False Positive Checklist."
        }]

        client = self._make_client()
        resp = client.chat(messages, system=system_prompt)

        if resp.startswith("API ERROR"):
            return {
                "warning": warning, "verdict": "API_ERROR", "confidence": "?",
                "rounds": 1, "full_response": resp, "reasoning": "", "fp_pattern": "", "fix": ""
            }

        parsed = parse_verdict(resp)

        if allow_confirm and parsed["confidence"] == "LOW":
            messages.append({"role": "assistant", "content": resp})
            messages.append({
                "role": "user",
                "content": (
                    "Your confidence is LOW. Please reconsider:\n"
                    "1. Are there any error paths with IS_ERR guards that you might have missed?\n"
                    "2. Is there an ownership transfer pattern (object stored in struct/list)?\n"
                    "3. Is there a deferred release mechanism (work_struct, timer, callback)?\n"
                    "4. Are the callee reports consistent with your analysis?\n\n"
                    "Output your FINAL VERDICT."
                )
            })
            resp2 = client.chat(messages, system=system_prompt)
            if not resp2.startswith("API ERROR"):
                parsed = parse_verdict(resp2)
                resp = resp2

        return {
            "warning": warning,
            "verdict": parsed["verdict"],
            "confidence": parsed["confidence"],
            "reasoning": parsed["reasoning"],
            "fp_pattern": parsed["fp_pattern"],
            "fix": parsed["fix"],
            "rounds": 2 if (allow_confirm and parsed["confidence"] == "LOW") else 1,
            "full_response": resp,
        }

    def run_batch_api(self, input_dir: str, output_file: str,
                      limit: int = 0, workers: int = 4,
                      allow_confirm: bool = False,
                      results_dir: str = None):
        """多线程批量审计 (断点续传)"""
        if results_dir is None:
            results_dir = input_dir
        os.makedirs(results_dir, exist_ok=True)

        context_files = sorted([
            f for f in os.listdir(input_dir)
            if f.endswith('.md') and not f.startswith('_') and not f.startswith('detail_')
        ])

        # 跳过已审计的 (检查独立结果目录)
        done = set(
            f.replace("detail_", "")
            for f in os.listdir(results_dir)
            if f.startswith('detail_')
        )
        pending = [f for f in context_files if f not in done]
        skipped = len(context_files) - len(pending)
        if skipped > 0:
            print(f"⏭ Skipping {skipped} already-audited files")

        if limit > 0:
            pending = pending[:limit]
        total = len(pending)
        if total == 0:
            print("All files already audited. Use --summary-only to regenerate report.")
            return

        print(f"\n{'='*60}")
        print(f"  Batch Audit: {total} files, {workers} workers")
        print(f"  API: {self.api_config.get('api_url', '?')}")
        print(f"  Model: {self.api_config.get('model', '?')}")
        print(f"{'='*60}\n")

        results_lock = threading.Lock()
        results = []
        completed_count = [0]
        error_count = [0]
        t0 = time.time()

        def audit_one(cf: str) -> dict:
            cpath = os.path.join(input_dir, cf)
            r = self.audit_single(cpath, allow_confirm=allow_confirm)
            w = r['warning']

            with results_lock:
                results.append(r)
                completed_count[0] += 1
                n = completed_count[0]
                elapsed = time.time() - t0
                rate = n / elapsed if elapsed > 0 else 0
                eta = (total - n) / rate if rate > 0 else 0

                v_icon = '🐛' if r['verdict'] == 'REAL BUG' else ('✅' if r['verdict'] == 'FALSE POSITIVE' else '❓')
                if r['verdict'] == 'API_ERROR':
                    error_count[0] += 1
                    v_icon = '💥'

                print(f"  [{n}/{total}] {v_icon} {w['file']}:{w['line']} {w['function']}() "
                      f"→ {r['verdict']} ({r['confidence']}, {r['rounds']}r) "
                      f"| {rate:.1f}/s ETA:{eta:.0f}s")

            # 写入 detail 文件 (断点续传)
            detail_file = os.path.join(results_dir, f"detail_{cf}")
            try:
                with open(detail_file, 'w') as f:
                    f.write(f"# Audit: {w['file']}:{w['line']} {w['function']}()\n\n")
                    f.write(f"**VERDICT**: {r['verdict']}\n")
                    f.write(f"**Confidence**: {r['confidence']}\n")
                    f.write(f"**Rounds**: {r['rounds']}\n")
                    f.write(f"**Auto Class**: {w.get('auto_class', '?')}\n")
                    if r.get('fp_pattern'):
                        f.write(f"**FP Pattern**: {r['fp_pattern']}\n")
                    if r.get('reasoning'):
                        f.write(f"\n### Reasoning\n\n{r['reasoning']}\n")
                    if r.get('fix'):
                        f.write(f"\n### Suggested Fix\n```c\n{r['fix']}\n```\n")
                    f.write(f"\n### Full Response\n\n{r['full_response']}\n")
            except IOError as e:
                print(f"  ⚠ Failed to write detail for {cf}: {e}")

            # 每 50 条保存一次中间汇总
            if n % 50 == 0:
                self._save_checkpoint(results, results_dir, output_file, n, total)

            return r

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(audit_one, cf): cf for cf in pending}
            concurrent.futures.wait(futures)
            for fut in futures:
                try:
                    fut.result()
                except Exception as e:
                    print(f"  💥 THREAD ERROR: {futures[fut]}: {e}")

        elapsed = time.time() - t0
        print(f"\n{'='*60}")
        print(f"  Done: {total} files in {elapsed:.0f}s ({total/elapsed:.1f}/s)")
        print(f"  Errors: {error_count[0]}")
        print(f"{'='*60}")

        self._write_report(results, input_dir, output_file)

    def _save_checkpoint(self, results: list, results_dir: str, output_file: str, n: int, total: int):
        """中间检查点保存"""
        checkpoint_file = output_file.replace('.md', f'_checkpoint_{n}of{total}.md')
        try:
            self._write_report(results, results_dir, checkpoint_file)
        except Exception:
            pass  # checkpoint 失败不影响主流程

    def _write_report(self, results: list, input_dir: str, output_file: str):
        """生成汇总报告"""
        # 按结果排序: REAL BUG first, then FALSE POSITIVE, then others
        def sort_key(r):
            v = r.get('verdict', 'UNCLEAR')
            if v == 'REAL BUG': return 0
            if v == 'FALSE POSITIVE': return 1
            return 2
        results_sorted = sorted(results, key=sort_key)

        real = [r for r in results if r['verdict'] == 'REAL BUG']
        fp = [r for r in results if r['verdict'] == 'FALSE POSITIVE']
        unclear = [r for r in results if r['verdict'] not in ('REAL BUG', 'FALSE POSITIVE')]
        api_err = [r for r in results if r['verdict'] == 'API_ERROR']

        # FP 模式统计
        fp_patterns = defaultdict(int)
        for r in fp:
            if r.get('fp_pattern'):
                fp_patterns[r['fp_pattern'][:80]] += 1

        # 子系统分布
        subsystem_fp = defaultdict(lambda: [0, 0])  # [FP, Total]
        for r in results:
            w = r['warning']
            subsys = w['file'].split('/')[0] if '/' in w['file'] else w['file']
            subsystem_fp[subsys][1] += 1
            if r['verdict'] == 'FALSE POSITIVE':
                subsystem_fp[subsys][0] += 1

        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, 'w') as f:
            f.write("# Batch Audit Report (s10_v2 Multi-threaded)\n\n")
            f.write(f"**Total**: {len(results)} | "
                    f"**Real Bugs**: {len(real)} | "
                    f"**False Positives**: {len(fp)} | "
                    f"**API Errors**: {len(api_err)} | "
                    f"**Unclear**: {len(unclear)}\n\n")

            if results:
                fp_rate = 100 * len(fp) / len(results)
                real_rate = 100 * len(real) / len(results)
                f.write(f"**False Positive Rate**: {fp_rate:.1f}%\n")
                f.write(f"**Real Bug Rate**: {real_rate:.1f}%\n\n")

            # FP 模式 Top 15
            if fp_patterns:
                f.write("## Top False Positive Patterns\n\n")
                f.write("| Pattern | Count |\n")
                f.write("|---------|-------|\n")
                for pat, cnt in sorted(fp_patterns.items(), key=lambda x: -x[1])[:15]:
                    f.write(f"| {pat} | {cnt} |\n")
                f.write("\n")

            # 子系统 FP 率
            f.write("## False Positive Rate by Subsystem\n\n")
            f.write("| Subsystem | FP/Total | FP Rate |\n")
            f.write("|-----------|----------|--------|\n")
            for subsys, (fp_c, total_c) in sorted(subsystem_fp.items(),
                                                    key=lambda x: -x[1][1]):
                rate = 100 * fp_c / total_c if total_c else 0
                f.write(f"| {subsys} | {fp_c}/{total_c} | {rate:.0f}% |\n")
            f.write("\n")

            # 详细结果
            f.write("## Detailed Results\n\n")
            f.write("| # | File:Line | Function | Verdict | Conf | Auto Class | Rounds |\n")
            f.write("|---|-----------|----------|---------|------|------------|--------|\n")
            for i, r in enumerate(results_sorted):
                w = r['warning']
                ac = w.get('auto_class', '?')
                v_map = {'REAL BUG': '🐛', 'FALSE POSITIVE': '✅',
                         'API_ERROR': '💥', 'UNCLEAR': '❓'}
                v_icon = v_map.get(r['verdict'], '❓')
                f.write(f"| {i+1} | {w['file']}:{w['line']} | {w['function']}() "
                        f"| {v_icon} {r['verdict']} | {r['confidence']} | {ac} | {r['rounds']} |\n")

            # Real Bugs 详情
            if real:
                f.write("\n## 🐛 Real Bugs\n\n")
                for r in real:
                    w = r['warning']
                    f.write(f"### {w['file']}:{w['line']} {w['function']}()\n")
                    f.write(f"- **Confidence**: {r['confidence']}\n")
                    if r.get('reasoning'):
                        f.write(f"- **Reasoning**: {r['reasoning'][:300]}\n")
                    if r.get('fix'):
                        f.write(f"- **Suggested Fix**:\n```c\n{r['fix']}\n```\n")
                    f.write("\n")

            # API Errors
            if api_err:
                f.write("\n## 💥 API Errors (需要重试)\n\n")
                for r in api_err:
                    w = r['warning']
                    f.write(f"- `{w['file']}:{w['line']}` `{w['function']}()`\n")

            f.write(f"\n---\n*Detailed responses: `detail_*.md` in `{input_dir}/`*\n")

        # 终端摘要
        print(f"\n{'='*60}")
        print(f"  Report: {output_file}")
        print(f"  🐛 Real Bugs:      {len(real)}")
        print(f"  ✅ False Positives: {len(fp)}")
        print(f"  💥 API Errors:      {len(api_err)}")
        print(f"  ❓ Unclear:         {len(unclear)}")
        if results and len(fp) + len(real) > 0:
            print(f"  FP Rate: {100*len(fp)/len(results):.1f}%")
        print(f"{'='*60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='s10_v2: Multi-threaded refcount audit engine')
    parser.add_argument('--input-dir', required=True, help='Directory of enriched context files')
    parser.add_argument('--results-dir', default=None, help='Directory for detail results (default: same as input-dir)')
    parser.add_argument('--output', default=None, help='Output report file')
    parser.add_argument('--template', default=TEMPLATE_FILE, help='Audit prompt template')
    parser.add_argument('--api', action='store_true', help='Use LLM API for auditing')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of warnings')
    parser.add_argument('--workers', type=int, default=4, help='Parallel workers (default: 4)')
    parser.add_argument('--confirm', action='store_true',
                        help='Allow second confirmation round for LOW confidence')
    parser.add_argument('--summary-only', action='store_true',
                        help='Regenerate report from existing detail files')
    args = parser.parse_args()

    if args.output is None:
        args.output = os.path.join(os.path.dirname(os.path.abspath(args.input_dir)) or '.',
                                   'audit_report_v2.md')

    # 汇总模式: 从已有 detail 文件重建报告
    if args.summary_only:
        engine = AuditEngineV2(args.template)
        detail_files = sorted([
            f for f in os.listdir(args.input_dir) if f.startswith('detail_')
        ])
        results = []
        for df in detail_files:
            dpath = os.path.join(args.input_dir, df)
            with open(dpath) as f:
                content = f.read()
            vm = re.search(r'\*\*VERDICT\*\*:\s*(.+)', content)
            cm = re.search(r'\*\*Confidence\*\*:\s*(.+)', content)
            rm = re.search(r'\*\*Rounds\*\*:\s*(\d+)', content)
            am = re.search(r'\*\*Auto Class\*\*:\s*(.+)', content)
            fpm = re.search(r'\*\*FP Pattern\*\*:\s*(.+)', content)
            wm = re.search(r'Audit:\s+(\S+):(\d+)\s+(\S+)\(\)', content)
            if wm:
                results.append({
                    'warning': {
                        'file': wm.group(1),
                        'line': int(wm.group(2)),
                        'function': wm.group(3),
                        'auto_class': am.group(1).strip() if am else '?',
                    },
                    'verdict': vm.group(1).strip() if vm else 'UNCLEAR',
                    'confidence': cm.group(1).strip() if cm else '?',
                    'rounds': int(rm.group(1)) if rm else 1,
                    'fp_pattern': fpm.group(1).strip() if fpm else '',
                    'reasoning': '',
                    'fix': '',
                    'full_response': '',
                })
        engine._write_report(results, args.input_dir, args.output)
        return

    # API 模式
    if args.api:
        cfg = load_api_config()
        if not cfg["api_key"]:
            print("ERROR: No API key found. Set ANTHROPIC_API_KEY or configure api_config.env")
            sys.exit(1)
        engine = AuditEngineV2(args.template, cfg)
        engine.run_batch_api(args.input_dir, args.output, args.limit, args.workers,
                             allow_confirm=args.confirm,
                             results_dir=args.results_dir)
    else:
        context_count = len([f for f in os.listdir(args.input_dir)
                            if f.endswith('.md') and not f.startswith('_') and not f.startswith('detail_')])
        print(f"Use --api for API-based auditing.")
        print(f"Found {context_count} context files in {args.input_dir}/")
        print(f"Add --workers N for parallel auditing (default 4).")


if __name__ == '__main__':
    main()
