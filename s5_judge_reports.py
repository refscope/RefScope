#!/usr/bin/env python3
"""
Judge Clang Static Analyzer HTML reports using an LLM API.
Given ~70% false-positive rate in these reports, the LLM is asked to carefully
evaluate each report's bug path against the actual code logic and determine
whether the warning is a true positive or false positive.

Usage:
    python judge_reports.py \
        --report-dir /path/to/reports \
        --api-key sk-xxx \
        --api-url https://api.deepseek.com \
        --model deepseek-v4-flash \
        --output results.json \
        --concurrency 5
"""

import argparse
import json
import os
import re
import sys
import time
import concurrent.futures
from pathlib import Path
from html import unescape as html_unescape

import requests


# ---------------------------------------------------------------------------
# HTML report parsing
# ---------------------------------------------------------------------------

_BUGMETA_RE = re.compile(r"<!-- (BUGDESC|BUGTYPE|BUGCATEGORY|BUGFILE|FILENAME|FUNCTIONNAME|BUGLINE|BUGCOLUMN|BUGPATHLENGTH) (.*?) -->")
_PATH_STEP_RE = re.compile(
    r'<div id="(Path\d+|EndPath)" class="msg (msgEvent|msgControl|msgNote)".*?'
    r'<div class="PathIndex[^"]*">(\d+)</div>.*?'
    r'<td>(.*?)</td>',
    re.DOTALL,
)
_WARNING_RE = re.compile(
    r'<tr><td class="rowname">Warning:</td><td>.*?<br />(.*?)</td></tr>',
    re.DOTALL,
)
_CODE_LINE_RE = re.compile(
    r'<tr class="codeline" data-linenumber="(\d+)">'
    r'<td class="num"[^>]*>.*?</td>'
    r'<td class="line">(.*?)</td></tr>',
    re.DOTALL,
)
_STRIP_HTML_TAGS = re.compile(r"<[^>]+>")


def _strip_html(text):
    """Remove HTML tags and decode entities."""
    text = _STRIP_HTML_TAGS.sub("", text)
    text = html_unescape(text)
    return text.strip()


def parse_report(filepath):
    """Extract structured information from a Clang HTML report."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    # Extract bug metadata from HTML comments
    meta = {}
    for m in _BUGMETA_RE.finditer(html):
        meta[m.group(1)] = m.group(2).strip()

    # Warning text
    warning_match = _WARNING_RE.search(html)
    warning_desc = _strip_html(warning_match.group(1)) if warning_match else ""

    # Path steps (the analyzer's reasoning chain)
    path_steps = []
    for m in _PATH_STEP_RE.finditer(html):
        step_id = m.group(1)
        msg_type = m.group(2)
        step_num = int(m.group(3))
        description = _strip_html(m.group(4))
        path_steps.append({
            "step": step_num,
            "id": step_id,
            "type": msg_type,
            "description": description,
        })
    # Sort by step number
    path_steps.sort(key=lambda x: x["step"])

    # Source code lines (extract all code for context)
    code_lines = {}
    for m in _CODE_LINE_RE.finditer(html):
        lineno = int(m.group(1))
        code = _strip_html(m.group(2))
        code_lines[lineno] = code

    bug_line = int(meta.get("BUGLINE", 0))

    # Collect relevant code context around the bug line
    context_start = max(1, bug_line - 30)
    context_end = bug_line + 30
    relevant_code = []
    for ln in sorted(code_lines):
        if context_start <= ln <= context_end:
            marker = " >>>" if ln == bug_line else "    "
            relevant_code.append(f"{marker} {ln:5d}: {code_lines[ln]}")

    return {
        "report_id": os.path.splitext(os.path.basename(filepath))[0],
        "filepath": filepath,
        "meta": meta,
        "warning_desc": warning_desc,
        "bug_line": bug_line,
        "path_steps": path_steps,
        "context_code": "\n".join(relevant_code),
    }


# ---------------------------------------------------------------------------
# LLM prompt building
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert C code reviewer specializing in Linux kernel memory management and reference counting. Your task is to evaluate Clang Static Analyzer bug reports and determine whether each one is a TRUE positive (real bug) or FALSE positive (incorrect warning).

## Critical Context
- These reports come from the Linux kernel codebase, which uses reference counting extensively (refcount_t, kref, get/put patterns).
- Approximately 70% of these static analyzer reports are FALSE POSITIVES.
- The analyzer often cannot understand complex control flow, error-handling gotos, or inter-procedural ownership semantics.

## How to Judge
For each report, carefully examine:
1. **The bug path**: Read each step the analyzer took. Does it make realistic assumptions about program state?
2. **The code context**: Look at the surrounding code. Does the warning location actually have a bug, or is the analyzer missing something?
3. **Memory/refcount ownership**: In kernel code, is the allocated memory or acquired reference properly released on all paths? Consider goto-based cleanup.
4. **Analyzer limitations**: The analyzer often assumes the worst-case path without considering:
   - Invariants enforced by the caller
   - Guards/checks that the analyzer couldn't prove
   - Custom allocator semantics
   - Macro-based reference counting patterns

## Output Format
Respond with a JSON object and nothing else:
```json
{
  "is_accurate": true/false,
  "confidence": "high/medium/low",
  "bug_type_actual": "real_bug_type_or_\"false_positive\"",
  "reason": "Concise explanation in Chinese, referencing specific steps/source lines"
}
```

- `is_accurate`: true if you believe this is a REAL bug (true positive), false if it's a false alarm
- `confidence`: your certainty level
- `bug_type_actual`: if false positive, use "false_positive". Otherwise classify the real bug type.
- `reason`: Explain your reasoning in Chinese, citing specific path steps and code lines. Keep it concise (2-5 sentences)."""


def build_user_prompt(report):
    """Build the user message for a single report."""
    meta = report["meta"]
    bug_desc = meta.get("BUGDESC", "Unknown")
    bug_type = meta.get("BUGTYPE", "Unknown")
    bug_category = meta.get("BUGCATEGORY", "Unknown")
    filename = meta.get("FILENAME", meta.get("BUGFILE", "Unknown"))
    function_name = meta.get("FUNCTIONNAME", "Unknown")
    bug_line = meta.get("BUGLINE", "?")

    parts = []
    parts.append(f"## Report ID: {report['report_id']}")
    parts.append(f"**Bug Description**: {bug_desc}")
    parts.append(f"**Bug Type**: {bug_type}")
    parts.append(f"**Bug Category**: {bug_category}")
    parts.append(f"**File**: {filename}")
    parts.append(f"**Function**: {function_name}")
    parts.append(f"**Warning Line**: {bug_line}")
    parts.append(f"**Warning**: {report['warning_desc']}")

    parts.append("\n### Analyzer Bug Path (Step by Step)")
    parts.append("The analyzer traced the following execution path to reach the warning:")
    for step in report["path_steps"]:
        step_type_label = {
            "msgEvent": "[EVENT]",
            "msgControl": "[CONTROL]",
            "msgNote": "[NOTE]",
        }.get(step["type"], f"[{step['type']}]")
        parts.append(f"  Step {step['step']} {step_type_label}: {step['description']}")

    parts.append("\n### Surrounding Source Code Context")
    parts.append("(>>> marks the warning line)")
    parts.append("```c")
    parts.append(report["context_code"])
    parts.append("```")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# API calling
# ---------------------------------------------------------------------------

class ReportJudge:
    def __init__(self, api_key, api_url, model, timeout=120):
        normalized_url = api_url.rstrip("/")
        if not normalized_url.endswith("/chat/completions"):
            normalized_url = f"{normalized_url}/chat/completions"
        self.api_url = normalized_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        self.model = model
        self.timeout = timeout

    def judge(self, report, retries=3):
        user_content = build_user_prompt(report)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 4096,
            "stream": False,
        }

        last_error = None
        for attempt in range(retries):
            try:
                resp = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                body = resp.json()
                content = body["choices"][0]["message"]["content"]

                # Extract JSON from response
                result = _extract_json(content)
                result["raw_response"] = content
                result["report_id"] = report["report_id"]
                result["report_file"] = report["filepath"]
                return result

            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)

        return {
            "report_id": report["report_id"],
            "report_file": report["filepath"],
            "is_accurate": None,
            "confidence": "error",
            "bug_type_actual": "api_error",
            "reason": f"API call failed after {retries} retries: {last_error}",
            "raw_response": "",
        }


def _extract_json(text):
    """Extract JSON object from LLM response text."""
    # Try to find JSON block between ```json and ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "is_accurate": None,
            "confidence": "parse_error",
            "bug_type_actual": "parse_error",
            "reason": f"Failed to parse JSON from: {text[:500]}",
        }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def collect_reports(report_dir):
    """Find all report HTML files in the given directory."""
    report_path = Path(report_dir)
    if not report_path.exists():
        print(f"Error: directory not found: {report_dir}")
        sys.exit(1)
    files = sorted(report_path.glob("report-*.html"))
    # Skip index.html
    files = [f for f in files if f.name != "index.html"]
    return [str(f) for f in files]


def process_one(args):
    """Process a single report file. (Top-level function for multiprocessing.)"""
    filepath, judge, report_index, total = args
    report = parse_report(filepath)
    result = judge.judge(report)
    result["index"] = report_index
    print(f"  [{report_index}/{total}] {report['report_id']}: "
          f"accurate={result.get('is_accurate')}, "
          f"confidence={result.get('confidence')}, "
          f"reason={result.get('reason', '')[:100]}",
          flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Judge Clang Static Analyzer reports using an LLM"
    )
    parser.add_argument(
        "--report-dir",
        default=os.environ.get("REFCOUNT_BUG_DIR", "./reports"),
        help="Directory containing report HTML files",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ANTHROPIC_AUTH_TOKEN",
                               os.environ.get("DEEPSEEK_API_KEY", "")),
        help="API key for the LLM service",
    )
    parser.add_argument(
        "--api-url",
        default="https://api.deepseek.com",
        help="API base URL (OpenAI-compatible chat completions endpoint)",
    )
    parser.add_argument(
        "--model",
        default="deepseek-v4-flash",
        help="Model name to use",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path (default: judge_results_<timestamp>.json in report-dir)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent API calls (default: 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit to first N reports (0 = all)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start from report index N (0-based, for resuming)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="API request timeout in seconds (default: 180)",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("Error: No API key provided. Set --api-key or ANTHROPIC_AUTH_TOKEN env var.")
        sys.exit(1)

    report_files = collect_reports(args.report_dir)
    total = len(report_files)
    print(f"Found {total} report files in {args.report_dir}")

    if args.start > 0:
        report_files = report_files[args.start:]
        print(f"Starting from index {args.start}, {len(report_files)} remaining")

    if args.limit > 0:
        report_files = report_files[: args.limit]
        print(f"Limited to first {args.limit} reports")

    if args.output is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        args.output = os.path.join(args.report_dir, f"judge_results_{ts}.json")

    judge = ReportJudge(args.api_key, args.api_url, args.model, timeout=args.timeout)

    # Warm-up: test connectivity with a simple call
    print(f"Testing API connectivity to {args.api_url} with model {args.model}...")
    try:
        test_payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": "Reply with just: OK"}],
            "temperature": 0,
            "max_tokens": 16,
            "stream": False,
        }
        normalized_url = args.api_url.rstrip("/")
        if not normalized_url.endswith("/chat/completions"):
            normalized_url = f"{normalized_url}/chat/completions"
        test_resp = requests.post(
            normalized_url,
            headers=judge.headers,
            json=test_payload,
            timeout=30,
        )
        test_resp.raise_for_status()
        print("  API connection OK")
    except Exception as exc:
        print(f"  API connection FAILED: {exc}")
        sys.exit(1)

    results = []
    start_time = time.time()
    success_count = 0
    fail_count = 0
    tp_count = 0
    fp_count = 0

    print(f"\nProcessing {len(report_files)} reports with {args.concurrency} concurrent workers...\n")

    tasks = [
        (f, judge, args.start + i + 1, total)
        for i, f in enumerate(report_files)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(process_one, t): t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                if result.get("is_accurate") is True:
                    tp_count += 1
                elif result.get("is_accurate") is False:
                    fp_count += 1
                if result.get("confidence") != "error":
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as exc:
                task = futures[future]
                filepath = task[0]
                report_id = os.path.splitext(os.path.basename(filepath))[0]
                results.append({
                    "report_id": report_id,
                    "report_file": filepath,
                    "is_accurate": None,
                    "confidence": "error",
                    "bug_type_actual": "exception",
                    "reason": str(exc),
                })
                fail_count += 1

    elapsed = time.time() - start_time

    # Sort results by index to maintain original order
    results.sort(key=lambda r: r.get("index", 0))

    # Remove index from output
    for r in results:
        r.pop("index", None)

    # Summary
    summary = {
        "total": len(results),
        "success": success_count,
        "failed": fail_count,
        "true_positives": tp_count,
        "false_positives": fp_count,
        "fp_rate": round(fp_count / max(tp_count + fp_count, 1), 3),
        "elapsed_seconds": round(elapsed, 1),
        "model": args.model,
        "report_dir": args.report_dir,
    }
    output = {
        "summary": summary,
        "results": results,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Results saved to: {args.output}")
    print(f"Total: {summary['total']} | Success: {summary['success']} | Failed: {summary['failed']}")
    print(f"True Positives: {summary['true_positives']} | False Positives: {summary['false_positives']}")
    print(f"False Positive Rate: {summary['fp_rate']:.1%}")
    print(f"Elapsed: {summary['elapsed_seconds']:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
