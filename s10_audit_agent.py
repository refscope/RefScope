#!/usr/bin/env python3
"""
s10_audit_agent.py — 迭代式 smatch refcount 告警审计 Agent

工作流:
  Round 1: 加载 s9 准备的上下文，发送给 LLM API
  Round 2+: 根据 LLM 请求，InfoCollector 获取额外源码，发送给 API
  Final:    解析 LLM 输出中的 VERDICT

Usage:
    python3 s10_audit_agent.py -c CONTEXT.md --api
    python3 s10_audit_agent.py --input-dir audit_contexts/ --api
    python3 s10_audit_agent.py -c CONTEXT.md --interactive
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
KERNEL_DIR = os.environ.get("REFCOUNT_KERNEL_DIR", "")
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(_SCRIPT_DIR, "template_audit_v1.md")
CONFIG_FILE = os.path.join(_SCRIPT_DIR, "api_config.env")


def load_api_config(config_file: str = None) -> dict:
    """从配置文件或环境变量加载 API 配置"""
    if config_file is None:
        config_file = CONFIG_FILE
    cfg = {
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "api_url": os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages"),
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        "max_rounds": int(os.environ.get("AUDIT_MAX_ROUNDS", "5")),
    }
    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "ANTHROPIC_API_KEY":   cfg["api_key"] = v
                elif k == "ANTHROPIC_API_URL":  cfg["api_url"] = v
                elif k == "ANTHROPIC_MODEL":    cfg["model"] = v
                elif k == "AUDIT_MAX_ROUNDS":   cfg["max_rounds"] = int(v)
    return cfg


# ---------------------------------------------------------------------------
# API 客户端
# ---------------------------------------------------------------------------
class APIClient:
    """调用兼容 API (Anthropic / OpenAI 格式自适应)"""

    def __init__(self, config: dict):
        self.api_key = config["api_key"]
        self.api_url = config["api_url"]
        self.model = config["model"]
        self.max_rounds = config["max_rounds"]
        # 检测 API 格式
        self._is_openai = "chat/completions" in self.api_url or "openai" in self.api_url.lower()

    def chat(self, messages: list, system: str = "", max_tokens: int = 4096) -> str:
        """发送消息到 API，返回文本响应"""
        if self._is_openai:
            return self._chat_openai(messages, system, max_tokens)
        return self._chat_anthropic(messages, system, max_tokens)

    def _chat_anthropic(self, messages: list, system: str, max_tokens: int) -> str:
        body = {"model": self.model, "max_tokens": max_tokens, "messages": []}
        if system: body["system"] = system
        body["messages"] = messages
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=data)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("anthropic-version", "2023-06-01")
        return self._send(req)

    def _chat_openai(self, messages: list, system: str, max_tokens: int) -> str:
        msgs = []
        if system: msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        body = {"model": self.model, "max_tokens": max_tokens, "messages": msgs}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=data)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        return self._send(req)

    def _send(self, req) -> str:
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                # Anthropic format
                if "content" in result and isinstance(result["content"], list):
                    for block in result["content"]:
                        if block.get("type") == "text":
                            return block["text"]
                # OpenAI format
                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                return str(result)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return f"API ERROR {e.code}: {body[:500]}"
        except Exception as e:
            return f"API ERROR: {str(e)}"

    def has_verdict(self, response: str) -> bool:
        """检查 API 响应是否包含最终判定"""
        return re.search(r'(?:VERDICT|判定)[:\s]*[{\"]?(?:REAL BUG|FALSE POSITIVE|真实|误报)', response, re.IGNORECASE) is not None

    def has_info_request(self, response: str) -> bool:
        """检查 API 响应是否请求更多信息"""
        patterns = [
            r'(?:Need|需要|请提供|show|read|get)\s+(?:source|源码|more|更多)',
            r'(?:source\s+(?:for|of)|read|查看)\s+\w+\s*(?:\(\))?\s*(?:at|in|@)',
            r'(?:struct|structure)\s+\w+\s*(?:in|from)',
        ]
        return any(re.search(p, response, re.IGNORECASE) for p in patterns)


# ---------------------------------------------------------------------------
# 信息收集器
# ---------------------------------------------------------------------------
class InfoCollector:
    def __init__(self, kernel_dir: str):
        self.kernel_dir = kernel_dir

    def resolve_file(self, filename: str) -> str:
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename
        full = os.path.join(self.kernel_dir, filename)
        if os.path.exists(full):
            return full
        try:
            result = subprocess.run(
                ["find", self.kernel_dir, "-name", os.path.basename(filename),
                 "-not", "-path", "*/.*"], capture_output=True, text=True, timeout=30)
            matches = [l for l in result.stdout.strip().split("\n") if l]
            if matches: return matches[0]
        except Exception: pass
        return None

    def read_function(self, filepath: str, function_name: str) -> str:
        full = self.resolve_file(filepath)
        if not full: return f"// FILE NOT FOUND: {filepath}"
        try:
            result = subprocess.run(
                ["grep", "-n", f"{function_name}\\s*\\(", full],
                capture_output=True, text=True, timeout=10)
            if not result.stdout.strip():
                return f"// FUNCTION NOT FOUND: {function_name} in {filepath}"
            lines = sorted(set(int(l.split(":")[0]) for l in result.stdout.strip().split("\n")))
            start = lines[0]  # definition is usually first occurrence
        except Exception: return f"// GREP FAILED"

        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
        out = []; depth = 0; started = False
        for i in range(start - 1, min(len(all_lines), start + 500)):
            ln = all_lines[i]; out.append(f"{i+1}: {ln.rstrip()}")
            if not started:
                if "{" in ln: started = True; depth += ln.count("{") - ln.count("}")
            else:
                depth += ln.count("{") - ln.count("}")
                if depth <= 0: break
        return "\n".join(out)

    def process_request(self, response: str) -> str:
        """解析 LLM 响应中的 [NEED_SOURCE] 标签并获取源码"""
        results = []

        # Pattern 1: [NEED_SOURCE] function_name
        for m in re.finditer(r'\[NEED_SOURCE\]\s+(\w+)', response):
            func = m.group(1)
            src = self._find_function_anywhere(func)
            results.append(f"[SOURCE] {func}()\n```c\n{src}\n```")

        # Pattern 2: [NEED_SOURCE] struct:struct_name
        for m in re.finditer(r'\[NEED_SOURCE\]\s+struct:(\w+)', response):
            struct = m.group(1)
            src = self._find_struct_anywhere(struct)
            results.append(f"[SOURCE] struct {struct}\n```c\n{src}\n```")

        return "\n\n".join(results) if results else ""

    def _find_function_anywhere(self, func_name: str) -> str:
        """在全部内核源码中查找函数定义（优先 cscope，回退 grep）"""
        # Try cscope first
        try:
            from accurate_func_locator import AccurateFuncLocator
            if not hasattr(self, '_cscope_locator'):
                self._cscope_locator = AccurateFuncLocator(self.kernel_dir)
            if self._cscope_locator.cscope_db_exists():
                r = self._cscope_locator.find_function_source(func_name)
                if r and r.get("confidence") in ("high", "medium"):
                    src = r.get("source_code", "")
                    start = r.get("start_line", 1)
                    # Add line numbers
                    numbered = []
                    for li, ln in enumerate(src.split("\n")):
                        numbered.append(f"{start + li}: {ln}")
                    return "\n".join(numbered)
        except Exception:
            pass

        # Fallback: grep in common locations
        try:
            result = subprocess.run(
                ["grep", "-rnE", f"^{func_name}\\s*\\(",
                 os.path.join(self.kernel_dir, "include"),
                 os.path.join(self.kernel_dir, "kernel"),
                 os.path.join(self.kernel_dir, "fs"),
                 os.path.join(self.kernel_dir, "drivers"),
                 os.path.join(self.kernel_dir, "net"),
                 os.path.join(self.kernel_dir, "mm"),
                 os.path.join(self.kernel_dir, "block"),
                 os.path.join(self.kernel_dir, "crypto"),
                 os.path.join(self.kernel_dir, "security"),
                 os.path.join(self.kernel_dir, "sound"),
                 os.path.join(self.kernel_dir, "lib"),
                 os.path.join(self.kernel_dir, "arch"),
                 ],
                capture_output=True, text=True, timeout=30, max_bytes=100000
            )
            if result.stdout.strip():
                first = result.stdout.strip().split("\n")[0]
                parts = first.split(":", 2)
                if len(parts) >= 2:
                    fpath = parts[0]
                    line = int(parts[1])
                    return self._extract_func(fpath, line)
        except Exception:
            pass
        return f"// FUNCTION NOT FOUND: {func_name}"

    def _find_struct_anywhere(self, struct_name: str) -> str:
        try:
            result = subprocess.run(
                ["grep", "-rnE", f"struct {struct_name}\\s*{{",
                 os.path.join(self.kernel_dir, "include")],
                capture_output=True, text=True, timeout=10, max_bytes=50000
            )
            if result.stdout.strip():
                first = result.stdout.strip().split("\n")[0]
                parts = first.split(":", 2)
                if len(parts) >= 2:
                    fpath = parts[0]
                    line = int(parts[1])
                    return self._extract_block(fpath, line)
        except Exception:
            pass
        return f"// STRUCT NOT FOUND: struct {struct_name}"

    def _extract_func(self, filepath: str, start: int) -> str:
        lines = read_source_lines(filepath)
        if not lines: return f"// FILE NOT FOUND"
        out = []; depth = 0; started = False
        for i in range(start - 1, min(len(lines), start + 600)):
            ln = lines[i]; out.append(f"{i+1}: {ln.rstrip()}")
            if not started:
                if "{" in ln: started = True; depth += ln.count("{") - ln.count("}")
            else:
                depth += ln.count("{") - ln.count("}")
                if depth <= 0: break
        return "\n".join(out)

    def _extract_block(self, filepath: str, start: int) -> str:
        lines = read_source_lines(filepath)
        if not lines: return f"// FILE NOT FOUND"
        out = []; depth = 0
        for i in range(start - 1, min(len(lines), start + 100)):
            ln = lines[i]; out.append(f"{i+1}: {ln.rstrip()}")
            depth += ln.count("{") - ln.count("}")
            if depth <= 0 and i > start - 1: break
        return "\n".join(out)


def read_source_lines(filepath: str):
    if not os.path.exists(filepath): return []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


# ---------------------------------------------------------------------------
# 审计引擎
# ---------------------------------------------------------------------------
class AuditEngine:
    def __init__(self, kernel_dir: str, template_file: str, api_client: APIClient = None):
        self.collector = InfoCollector(kernel_dir)
        self.api = api_client
        self.template = ""
        if os.path.exists(template_file):
            with open(template_file) as f: self.template = f.read()

    def audit_single(self, context_file: str, output_file: str = None, verbose: bool = True) -> dict:
        """使用 API 审计单条告警"""
        with open(context_file) as f: context = f.read()
        wm = re.search(r'(?:\*\*)?File(?:\*\*)?:\s+(\S+):(\d+)', context)
        fm = re.search(r'(?:\*\*)?Function(?:\*\*)?:\s+(\S+)\(\)', context)
        warning = {
            "file": wm.group(1) if wm else "?", "line": wm.group(2) if wm else "?",
            "function": fm.group(1) if fm else "?",
        }

        system_prompt = self.template if self.template else "You audit kernel refcount bugs."
        messages = []
        round_prompt = f"## Audit this smatch refcount warning\n\n{context}"
        messages.append({"role": "user", "content": round_prompt})

        if verbose:
            print(f"  Auditing {warning['file']}:{warning['line']} {warning['function']}()...")

        max_rounds = self.api.max_rounds if self.api else 10

        for round_num in range(max_rounds):
            is_last_round = (round_num == max_rounds - 1)

            if is_last_round:
                messages.append({"role": "user",
                    "content": "[SYSTEM] This is the FINAL round. You MUST output your VERDICT now. "
                               "Based on ALL the source code you have gathered, make your best judgment. "
                               "Output VERDICT: REAL_BUG or FALSE_POSITIVE with reasoning. "
                               "If you are uncertain, state your confidence level as LOW."})

            resp = self.api.chat(messages, system=system_prompt)
            if resp.startswith("API ERROR"):
                if verbose: print(f" → API FAILED: {resp[:100]}")
                return {"warning": warning, "verdict": "API_ERROR", "confidence": "?",
                        "rounds": round_num+1, "full_response": resp}
            if verbose: print(f"    Round {round_num+1}: {len(resp)} chars", end="")

            # Check for VERDICT
            verdict_m = re.search(r'VERDICT[:\s]*[{\"\']?(REAL[_ ]BUG|FALSE[_ ]POSITIVE)', resp, re.IGNORECASE)
            has_need_source = '[NEED_SOURCE]' in resp and not is_last_round

            if verdict_m and not has_need_source:
                v = verdict_m.group(1).replace('_', ' ')
                conf_m = re.search(r'(?:Confidence|CONFIDENCE)[:\s]*[{\"\']?(HIGH|MEDIUM|LOW)', resp, re.IGNORECASE)
                conf = conf_m.group(1) if conf_m else "?"
                if verbose: print(f" → {v} ({conf})")

                audit_dir = os.path.dirname(context_file)
                detail_file = os.path.join(audit_dir, f"detail_{os.path.basename(context_file)}")
                # Extract seq number from context filename (e.g., 0001_xxx.md → 1)
                seq_m = re.match(r'(\d+)_', os.path.basename(context_file))
                seq = seq_m.group(1) if seq_m else "?"
                with open(detail_file, "w") as f:
                    f.write(f"# Audit #{seq}: {warning['file']}:{warning['line']} {warning['function']}()\n\n")
                    f.write(f"**VERDICT**: {v}\n**Confidence**: {conf}\n**Rounds**: {round_num+1}\n\n")
                    f.write(f"## Full Agent Response\n\n{resp}\n")

                return {"warning": warning, "verdict": v, "confidence": conf,
                        "rounds": round_num+1, "full_response": resp,
                        "detail_file": detail_file}

            # Check for [NEED_SOURCE] — fetch and continue
            fetched = self.collector.process_request(resp)
            if fetched.strip() and not is_last_round:
                n_funcs = fetched.count('[SOURCE]')
                if verbose: print(f" → fetched {n_funcs} function(s)")
                messages.append({"role": "assistant", "content": resp})
                messages.append({"role": "user",
                    "content": f"[SYSTEM] Source code:\n\n{fetched}\n\n"
                               f"Continue analysis. Request more with [NEED_SOURCE] or output VERDICT."})
                continue

            # No verdict, no source, not last — nudge
            if verbose: print(f" → continuing")
            messages.append({"role": "assistant", "content": resp})
            if not is_last_round:
                messages.append({"role": "user",
                    "content": "Use [NEED_SOURCE] to request source, or output VERDICT with reasoning."})

        # Should not reach here with final-round enforcement, but guard
        return {"warning": warning, "verdict": "UNCLEAR", "reason": "Internal error",
                "rounds": max_rounds, "full_response": ""}

    def _write_summary_from_details(self, input_dir: str, output_file: str):
        """从 detail_*.md 文件头读取 Verdict/Conf/Rounds，按报告序号排序"""
        detail_files = sorted([f for f in os.listdir(input_dir)
                               if f.startswith("detail_") and f.endswith(".md")])
        if not detail_files:
            print("No detail_*.md files found in", input_dir)
            return
        rows = []
        for df in detail_files:
            # Extract sequence number: detail_0001_... → 1
            seq_m = re.match(r'detail_(\d+)_', df)
            seq = int(seq_m.group(1)) if seq_m else 99999
            dpath = os.path.join(input_dir, df)
            with open(dpath) as f:
                header = "".join(f.readline() for _ in range(5))
            fm = re.search(r'Audit\s*(?:#\d+)?:\s+(\S+):(\d+)\s+(\S+)\(\)', header)
            vm = re.search(r'\*\*VERDICT\*\*:\s*(.+)', header)
            cm = re.search(r'\*\*Confidence\*\*:\s*(.+)', header)
            rm = re.search(r'\*\*Rounds\*\*:\s*(\d+)', header)
            if fm and vm:
                rows.append({
                    "seq": seq,
                    "file": fm.group(1), "line": fm.group(2), "func": fm.group(3),
                    "verdict": vm.group(1).strip(),
                    "conf": cm.group(1).strip() if cm else "?",
                    "rounds": int(rm.group(1)) if rm else 0,
                })
        # Sort by report sequence number
        rows.sort(key=lambda r: r["seq"])
        real = sum(1 for r in rows if "REAL" in r["verdict"].upper())
        fp = sum(1 for r in rows if "FALSE" in r["verdict"].upper())
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write("# Batch Audit Summary\n\n")
            f.write(f"Total: {len(rows)} | Real: {real} | FP: {fp}\n\n")
            f.write("| Seq | File:Line | Function | Verdict | Conf | Rounds |\n")
            f.write("|-----|-----------|----------|---------|------|--------|\n")
            for r in rows:
                f.write(f"| {r['seq']} | {r['file']}:{r['line']} | {r['func']}() | {r['verdict']} | {r['conf']} | {r['rounds']} |\n")
            f.write(f"\n**Real: {real} | FP: {fp} | Other: {len(rows)-real-fp}**\n")
            f.write(f"\nDetailed reports: `detail_*.md` in `{input_dir}/`.\n")
        print(f"Summary: {len(rows)} entries, Real={real}, FP={fp} → {output_file}")

    def run_batch(self, input_dir: str, output_file: str, limit: int = 0, workers: int = 1):
        import concurrent.futures, threading
        # Only audit context files that don't have a detail report yet
        all_context = sorted([f for f in os.listdir(input_dir)
                              if f.endswith(".md") and not f.startswith("detail_")
                              and not f.startswith("audit_")])
        done = set(f.replace("detail_", "") for f in os.listdir(input_dir) if f.startswith("detail_"))
        context_files = [f for f in all_context if f not in done]
        skipped = len(all_context) - len(context_files)
        if skipped > 0:
            print(f"Skipping {skipped} already-audited files")
        if limit > 0: context_files = context_files[:limit]
        total = len(context_files)
        if total == 0:
            print("All context files already audited. Use --summary-only to regenerate.")
            return
        print(f"Starting parallel audit: {total} files, {workers} workers\n")

        results_lock = threading.Lock()
        results = []
        completed = [0]

        def audit_one(cf: str) -> dict:
            cpath = os.path.join(input_dir, cf)
            r = self.audit_single(cpath, verbose=False)
            with results_lock:
                results.append(r)
                completed[0] += 1
                w = r["warning"]
                print(f"  [{completed[0]}/{total}] {w['file']}:{w['line']} {w['function']}() → {r['verdict']} ({r['rounds']}r)")
            return r

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(audit_one, cf): cf for cf in context_files}
            concurrent.futures.wait(futures)
            # Check for exceptions
            for fut in futures:
                try:
                    fut.result()
                except Exception as e:
                    print(f"  ERROR: {futures[fut]}: {e}")

        # Sort results by original order
        results.sort(key=lambda r: int(re.search(r'(\d+)', os.path.basename(
            r.get("detail_file", "0000"))).group(1)) if re.search(r'(\d+)', os.path.basename(
            r.get("detail_file", "0000"))) else 0)

        self._write_summary_from_details(input_dir, output_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Iterative smatch refcount audit agent")
    parser.add_argument("-c", "--context", help="Single context file")
    parser.add_argument("--input-dir", help="Directory of context files")
    parser.add_argument("--output", default=None, help="Output report file")
    parser.add_argument("--kernel-dir", default=KERNEL_DIR)
    parser.add_argument("--template", default=TEMPLATE_FILE)
    parser.add_argument("--api", action="store_true", help="Use LLM API for auditing")
    parser.add_argument("--interactive", action="store_true", help="Interactive manual mode")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of warnings")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers (default: 1)")
    parser.add_argument("--summary-only", action="store_true", help="Regenerate summary from existing detail files")
    args = parser.parse_args()

    if args.output is None:
        if args.input_dir:
            args.output = os.path.join(os.path.dirname(os.path.abspath(args.input_dir)) or ".", "audit_summary.md")
        else:
            args.output = "audit_report.md"

    api_client = None
    if args.api:
        cfg = load_api_config()
        if not cfg["api_key"]:
            print("ERROR: No API key found. Set ANTHROPIC_API_KEY or configure api_config.env")
            sys.exit(1)
        api_client = APIClient(cfg)
        print(f"API: {cfg['api_url']} | Model: {cfg['model']}")

    engine = AuditEngine(args.kernel_dir, args.template, api_client)

    if args.context and args.api:
        engine.audit_single(args.context, args.output)
    elif args.input_dir and args.api and not args.summary_only:
        engine.run_batch(args.input_dir, args.output, args.limit, args.workers)
    elif args.input_dir and args.summary_only:
        engine._write_summary_from_details(args.input_dir, args.output)
    elif args.context:
        print(f"Context: {args.context}")
        print("Use --api for automated audit, or --interactive for manual mode.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
