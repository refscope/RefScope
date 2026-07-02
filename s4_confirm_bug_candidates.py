#!/usr/bin/env python3
import json
import os
from pathlib import Path


PAIR_CANDIDATE_FILENAME = "function_pair_candidates.json"
DEFAULT_OUTPUT_FILENAME = "confirmed_bug_candidates_input.json"


def load_pair_candidates(function_result_dir):
    pair_candidate_path = os.path.join(function_result_dir, PAIR_CANDIDATE_FILENAME)
    with open(pair_candidate_path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_report_files(report_dir):
    report_path = Path(report_dir)
    if not report_path.exists():
        return []
    return sorted(str(path) for path in report_path.rglob("*.plist"))


def build_confirmation_input(function_result_dir, report_dir, output_file=None):
    pair_candidates = load_pair_candidates(function_result_dir)
    report_files = collect_report_files(report_dir)

    payload = {
        "schema_version": "bug-confirmation-input.v1",
        "pair_candidates": pair_candidates,
        "checker_reports": report_files,
        "instructions": {
            "goal": "Use Claude Code to confirm whether checker-reported refcount issues are likely true positives.",
            "required_context": [
                "warning location",
                "matched pair candidate",
                "relevant code snippet",
                "ownership transfer or cleanup evidence"
            ]
        }
    }

    if output_file is None:
        output_file = os.path.join(function_result_dir, DEFAULT_OUTPUT_FILENAME)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return output_file


if __name__ == "__main__":
    function_result_dir = os.environ.get(
        "REFCOUNT_FUNCTION_RESULT_DIR",
        os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "FunctionResult", "default")
    )
    report_dir = os.environ.get(
        "REFCOUNT_BUG_DIR",
        os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "Bug", "default")
    )
    output_file = build_confirmation_input(function_result_dir, report_dir)
    print(output_file)
