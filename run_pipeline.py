#!/usr/bin/env python3
"""
run_pipeline.py — RefScope 自动执行脚本

通过超参数控制 s1-s10 流水线的执行。支持完整流水线或部分阶段运行。

使用示例:
  # 运行完整流水线
  python3 run_pipeline.py --pipeline s1-s10 --kernel-dir /path/to/linux

  # 仅运行 s1（包装器分析）
  python3 run_pipeline.py --pipeline s1 --kernel-dir /path/to/linux

  # 运行 s6-s8（Smatch 检测）
  python3 run_pipeline.py --pipeline s6-s8 --data-dir /path/to/FunctionResult

  # 运行 s8-s10（跨函数检测 + 审计）
  python3 run_pipeline.py --pipeline s8-s10 --kernel-dir /path/to/linux

  # 预览模式
  python3 run_pipeline.py --pipeline s1-s10 --dry-run

  # 使用配置文件
  python3 run_pipeline.py --config my_config.env --pipeline s1-s10
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# 路径常量 — 指向本脚本所在目录（RefScope/）
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保 RefScope 目录在 sys.path 中，以便导入各 stage 模块
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ---------------------------------------------------------------------------
# 默认超参数
# ---------------------------------------------------------------------------
DEFAULTS: Dict[str, Any] = {
    "pipeline": "s1-s10",
    "kernel_dir": os.environ.get("REFCOUNT_KERNEL_DIR", ""),
    "data_dir": os.environ.get("REFCOUNT_DATA_DIR", "./data"),
    "smatch_dir": "./smatch",  # resolved relative to SCRIPT_DIR at runtime
    "smatch_result_base": os.environ.get("REFCOUNT_SMATCH_RESULT_DIR", os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "SmatchResult")),
    "function_result_dir": os.environ.get("REFCOUNT_FUNCTION_RESULT_DIR", ""),
    "location_info_dir": os.environ.get("REFCOUNT_TARGET_INFO_DIR", ""),
    "report_dir": os.environ.get("REFCOUNT_BUG_DIR", ""),
    "clang_dir": os.environ.get("REFCOUNT_CLANG_DIR", ""),
    "project_name": os.environ.get("REFCOUNT_PROJECT_NAME", "refscope-run"),
    "api_key": os.environ.get("REFCOUNT_API_KEY",
                               os.environ.get("ANTHROPIC_API_KEY",
                               os.environ.get("DEEPSEEK_API_KEY", ""))),
    "api_url": os.environ.get("REFCOUNT_API_URL", "https://api.deepseek.com"),
    "model": os.environ.get("REFCOUNT_MODEL", "deepseek-v4-flash"),
    "jobs": os.cpu_count() or 4,
    "smatch_config": "allyesconfig",
    "target_dir": "",
    "target_file": "",
    "concurrency": 5,
    "workers": 4,
    "limit": 0,
    "max_depth": 3,
    "interactive": False,
    "dry_run": False,
    "skip_config": False,
    "build_smatch": False,
    "config_file": "template_api_config.env",  # fallback to template if api_config.env missing
}

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def resolve_path(path: str) -> str:
    """解析路径：相对路径相对于 SCRIPT_DIR 展开，绝对路径保持不变。"""
    if not path:
        return path
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(SCRIPT_DIR, path))


# ---------------------------------------------------------------------------
# 流水线阶段定义
# ---------------------------------------------------------------------------
PIPELINE_STAGES = ["s1", "s2", "s3", "s4", "s5", "s6", "s6b", "s7", "s8", "s9", "s10"]

# 阶段别名映射：s9→s9_v3, s10→s10_v3 (默认使用最新版本)
STAGE_ALIAS = {
    "s1": "s1",
    "s2": "s2",
    "s3": "s3",
    "s4": "s4",
    "s5": "s5",
    "s6": "s6",
    "s6b": "s6b",
    "s7": "s7",
    "s8": "s8",
    "s9": "s9_v3",      # 默认 v3 契约上下文
    "s10": "s10_v3",    # 默认 v3 批量审计
}


def parse_pipeline(pipeline_spec: str) -> List[str]:
    """解析流水线范围字符串，返回需要执行的阶段列表。

    Args:
        pipeline_spec: 如 "s1-s10", "s6-s8", "s1", "s8-s10"

    Returns:
        阶段名称列表（如 ["s1","s2",...,"s10"]）
    """
    spec = pipeline_spec.strip().lower()

    if "-" in spec:
        parts = spec.split("-")
        start_stage = parts[0]
        end_stage = parts[1]

        # 提取数字
        start_num = int(start_stage.lstrip("s"))
        end_num = int(end_stage.lstrip("s"))

        stages = []
        for i in range(start_num, end_num + 1):
            stage_name = f"s{i}"
            if stage_name in PIPELINE_STAGES:
                stages.append(stage_name)
        return stages
    else:
        # 单个阶段
        if spec in PIPELINE_STAGES:
            return [spec]
        else:
            print(f"Warning: Unknown stage '{spec}', treating as full pipeline")
            return list(PIPELINE_STAGES)


def load_config_file(config_path: str) -> Dict[str, str]:
    """加载配置文件（.env 格式: KEY=VALUE）。"""
    config = {}
    if not os.path.exists(config_path):
        return config
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def merge_config(cfg: Dict[str, Any], env_config: Dict[str, str]) -> Dict[str, Any]:
    """将 .env 配置合并到参数字典中（命令行参数优先级更高）。"""
    key_map = {
        "ANTHROPIC_API_KEY": "api_key",
        "ANTHROPIC_AUTH_TOKEN": "api_key",
        "DEEPSEEK_API_KEY": "api_key",
        "API_URL": "api_url",
        "API_BASE_URL": "api_url",
        "MODEL": "model",
        "KERNEL_DIR": "kernel_dir",
        "SMATCH_DIR": "smatch_dir",
        "DATA_DIR": "data_dir",
    }
    for env_key, cfg_key in key_map.items():
        if env_key in env_config and not cfg.get(cfg_key):
            cfg[cfg_key] = env_config[env_key]
    return cfg


# =========================================================================
# Stage 执行函数
# =========================================================================

def run_s1(cfg: Dict[str, Any]) -> int:
    """Stage 1: 包装器分析 — 多 Agent 分析 refcount 包装器函数。"""
    print("\n" + "=" * 60)
    print("[S1] Caller Function Agent — 包装器分析")
    print("=" * 60)

    from s1_caller_function_agent import cf_chat_init

    init_func_list = [
        "refcount_set", "refcount_set_release",
        "refcount_add_not_zero", "refcount_add_not_zero_acquire",
        "refcount_add", "refcount_inc_not_zero", "refcount_inc_not_zero_acquire",
        "refcount_inc", "refcount_dec", "refcount_dec_and_test",
        "refcount_dec_if_one", "refcount_dec_not_one",
        "refcount_dec_and_mutex_lock", "refcount_dec_and_lock",
        "refcount_dec_and_lock_irqsave",
        "kref_init", "kref_get", "kref_put",
        "kref_put_mutex", "kref_put_lock", "kref_get_unless_zero",
    ]

    if cfg["dry_run"]:
        print(f"  [DRY RUN] 将分析 {len(init_func_list)} 个初始函数")
        print(f"  [DRY RUN] Kernel: {cfg['kernel_dir']}")
        print(f"  [DRY RUN] Data:   {cfg['data_dir']}")
        print(f"  [DRY RUN] Project: {cfg['project_name']}")
        print(f"  [DRY RUN] Model:  {cfg['model']}")
        return 0

    cf_chat_init(
        init_target_func_name_list=init_func_list,
        DataShare_dir=cfg["data_dir"],
        proj_name=cfg["project_name"],
        api_key=cfg["api_key"],
        api_url=cfg["api_url"],
        location_info_dir=cfg["location_info_dir"],
        model=cfg["model"],
        linux_dir=cfg["kernel_dir"],
    )
    print("[S1] 完成")
    return 0


def run_s2(cfg: Dict[str, Any]) -> int:
    """Stage 2: 生成 get/put 配对候选。"""
    print("\n" + "=" * 60)
    print("[S2] Get Function Pairs — 配对候选生成")
    print("=" * 60)

    from s2_get_function_pairs import get_function_pairs

    func_dir = os.path.join(cfg["data_dir"], "FunctionResult", cfg["project_name"])
    if not os.path.isdir(func_dir):
        # 回退到通用 function_result_dir
        func_dir = cfg.get("function_result_dir", func_dir)

    print(f"  Function result dir: {func_dir}")

    if cfg["dry_run"]:
        print("  [DRY RUN] 将从 refcount_callgraph.json 生成 function_pair_candidates.json")
        return 0

    get_function_pairs(func_dir)
    print("[S2] 完成")
    return 0


def run_s3(cfg: Dict[str, Any]) -> int:
    """Stage 3: 重建 Clang 检测器。"""
    print("\n" + "=" * 60)
    print("[S3] Rebuild Checker — 检测器重建")
    print("=" * 60)
    # s3 没有 argparse，直接在 __main__ 中执行，用 subprocess 运行
    script = os.path.join(SCRIPT_DIR, "s3_rebuild_checker.py")

    if cfg["dry_run"]:
        print(f"  [DRY RUN] python3 {script}")
        return 0

    result = subprocess.run([sys.executable, script], cwd=SCRIPT_DIR)
    print(f"[S3] 完成 (exit={result.returncode})")
    return result.returncode


def run_s4(cfg: Dict[str, Any]) -> int:
    """Stage 4: 确认 Bug 候选。"""
    print("\n" + "=" * 60)
    print("[S4] Confirm Bug Candidates — 候选确认")
    print("=" * 60)

    from s4_confirm_bug_candidates import build_confirmation_input

    func_dir = os.path.join(cfg["data_dir"], "FunctionResult", cfg["project_name"])
    report_dir = os.path.join(cfg["report_dir"], cfg["project_name"])
    if not os.path.isdir(func_dir):
        func_dir = cfg.get("function_result_dir", func_dir)

    print(f"  Function result dir: {func_dir}")
    print(f"  Report dir: {report_dir}")

    if cfg["dry_run"]:
        print("  [DRY RUN] 将生成 confirmed_bug_candidates_input.json")
        return 0

    build_confirmation_input(func_dir, report_dir)
    print("[S4] 完成")
    return 0


def run_s5(cfg: Dict[str, Any]) -> int:
    """Stage 5: LLM 判定检测报告。"""
    print("\n" + "=" * 60)
    print("[S5] Judge Reports — 报告判定")
    print("=" * 60)

    script = os.path.join(SCRIPT_DIR, "s5_judge_reports.py")
    cmd = [
        sys.executable, script,
        "--report-dir", cfg.get("report_dir", DEFAULTS["report_dir"]),
        "--api-key", cfg["api_key"],
        "--api-url", cfg["api_url"],
        "--model", cfg["model"],
        "--concurrency", str(cfg.get("concurrency", DEFAULTS["concurrency"])),
    ]
    if cfg.get("limit"):
        cmd += ["--limit", str(cfg["limit"])]

    print(f"  Report dir: {cfg.get('report_dir')}")

    if cfg["dry_run"]:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return 0

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    print(f"[S5] 完成 (exit={result.returncode})")
    return result.returncode


def run_s6(cfg: Dict[str, Any]) -> int:
    """Stage 6: 配置 Smatch 引用计数检测规则。"""
    print("\n" + "=" * 60)
    print("[S6] Configure Smatch — Smatch 配置")
    print("=" * 60)

    smatch_dir = resolve_path(cfg["smatch_dir"])
    script = os.path.join(SCRIPT_DIR, "s6_configure_smatch_refcount.py")
    cmd = [
        sys.executable, script,
        "--data-dir", cfg.get("function_result_dir", DEFAULTS["function_result_dir"]),
        "--output", os.path.join(smatch_dir, "smatch_refcount_info.c"),
    ]

    if cfg["dry_run"]:
        cmd.append("--dry-run")
        print(f"  [DRY RUN] {' '.join(cmd)}")
    else:
        print(f"  Data dir: {cfg.get('function_result_dir')}")
        print(f"  Output:   {os.path.join(smatch_dir, 'smatch_refcount_info.c')}")

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    print(f"[S6] 完成 (exit={result.returncode})")
    return result.returncode


def run_s6b(cfg: Dict[str, Any]) -> int:
    """Stage 6b: 自动清理 Bug 检测。"""
    print("\n" + "=" * 60)
    print("[S6b] Detect Auto-Cleanup Bugs — 自动清理检测")
    print("=" * 60)

    script = os.path.join(SCRIPT_DIR, "s6b_detect_auto_cleanup_bugs.py")
    cmd = [
        sys.executable, script,
        "--data-dir", cfg.get("function_result_dir", DEFAULTS["function_result_dir"]),
        "--kernel-dir", cfg["kernel_dir"],
    ]
    if cfg.get("limit"):
        cmd += ["--limit", str(cfg["limit"])]

    if cfg["dry_run"]:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return 0

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    print(f"[S6b] 完成 (exit={result.returncode})")
    return result.returncode


def run_s7(cfg: Dict[str, Any]) -> int:
    """Stage 7: 运行 Smatch 函数内检测。"""
    print("\n" + "=" * 60)
    print("[S7] Run Smatch Refcount — 函数内检测")
    print("=" * 60)

    script = os.path.join(SCRIPT_DIR, "s7_run_smatch_refcount.sh")
    cmd = ["bash", script]
    cmd += ["--jobs", str(cfg.get("jobs", DEFAULTS["jobs"]))]

    if cfg.get("smatch_config") == "allyesconfig":
        cmd.append("--allyesconfig")
    if cfg.get("skip_config"):
        cmd.append("--skip-config")
    if cfg.get("build_smatch"):
        cmd.append("--build-smatch")
    if cfg.get("target_dir"):
        cmd += ["--target-dir", cfg["target_dir"]]
    if cfg.get("target_file"):
        cmd += ["--target-file", cfg["target_file"]]

    # 解析 smatch 目录（支持相对路径）
    smatch_dir = resolve_path(cfg["smatch_dir"])

    # 覆盖 shell 脚本中的路径（通过环境变量）
    env = os.environ.copy()
    env["SMATCH_BIN"] = os.path.join(smatch_dir, "smatch")
    env["SMATCH_SRC_DIR"] = smatch_dir
    env["KERNEL_DIR"] = cfg["kernel_dir"]

    print(f"  Smatch:  {smatch_dir}")
    print(f"  Kernel:  {cfg['kernel_dir']}")

    if cfg["dry_run"]:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return 0

    result = subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
    print(f"[S7] 完成 (exit={result.returncode})")
    return result.returncode


def run_s8(cfg: Dict[str, Any]) -> int:
    """Stage 8: 运行 Smatch 过程间（跨函数）检测。"""
    print("\n" + "=" * 60)
    print("[S8] Run Smatch Cross-Func — 跨函数检测")
    print("=" * 60)

    script = os.path.join(SCRIPT_DIR, "s8_run_smatch_crossfunc.sh")
    cmd = ["bash", script]
    cmd += ["--jobs", str(cfg.get("jobs", DEFAULTS["jobs"]))]

    if cfg.get("smatch_config") == "allyesconfig":
        cmd.append("--allyesconfig")
    if cfg.get("skip_config"):
        cmd.append("--skip-config")
    if cfg.get("build_smatch"):
        cmd.append("--build-smatch")
    if cfg.get("target_dir"):
        cmd += ["--target-dir", cfg["target_dir"]]
    if cfg.get("target_file"):
        cmd += ["--target-file", cfg["target_file"]]

    # 解析 smatch 目录（支持相对路径）
    smatch_dir = resolve_path(cfg["smatch_dir"])

    env = os.environ.copy()
    env["SMATCH_BIN"] = os.path.join(smatch_dir, "smatch")
    env["SMATCH_SRC_DIR"] = smatch_dir
    env["KERNEL_DIR"] = cfg["kernel_dir"]

    print(f"  Smatch:  {smatch_dir}")
    print(f"  Kernel:  {cfg['kernel_dir']}")

    if cfg["dry_run"]:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return 0

    result = subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
    print(f"[S8] 完成 (exit={result.returncode})")
    return result.returncode


def run_s9(cfg: Dict[str, Any]) -> int:
    """Stage 9: 准备审计上下文（默认 v3 契约上下文）。"""
    print("\n" + "=" * 60)
    print("[S9] Prepare Audit Context — 审计上下文准备 (v3)")
    print("=" * 60)

    script = os.path.join(SCRIPT_DIR, "s9_v3_contract_context.py")
    warns_file = cfg.get("warns_file") or ""
    output_dir = cfg.get("output_dir") or os.path.join(cfg["data_dir"], "AuditContext", cfg["project_name"])
    func_dir = os.path.join(cfg["data_dir"], "FunctionResult", cfg["project_name"])
    if not os.path.isdir(func_dir):
        func_dir = cfg.get("function_result_dir", func_dir)

    if not warns_file:
        # 尝试从最新 smatch 结果中查找
        smatch_result = cfg.get("smatch_result_base", DEFAULTS["smatch_result_base"])
        if os.path.isdir(smatch_result):
            subdirs = sorted(os.listdir(smatch_result), reverse=True)
            for sd in subdirs:
                candidate = os.path.join(smatch_result, sd, "pass2_refcount_warns.txt")
                if os.path.isfile(candidate):
                    warns_file = candidate
                    print(f"  自动检测 warns 文件: {warns_file}")
                    break

    if not warns_file or not os.path.isfile(warns_file):
        print("  [SKIP] 未找到 warns 文件，请先运行 s8 或通过 --warns-file 指定")
        return 1

    cmd = [
        sys.executable, script,
        "--warns", warns_file,
        "--func-dir", func_dir,
        "--output-dir", output_dir,
        "--kernel-dir", cfg["kernel_dir"],
    ]
    if cfg.get("limit"):
        cmd += ["--limit", str(cfg["limit"])]

    print(f"  Warns:     {warns_file}")
    print(f"  Func dir:  {func_dir}")
    print(f"  Output:    {output_dir}")

    if cfg["dry_run"]:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return 0

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    print(f"[S9] 完成 (exit={result.returncode})")
    return result.returncode


def run_s10(cfg: Dict[str, Any]) -> int:
    """Stage 10: 审计 Agent（默认 v3 批量审计）。"""
    print("\n" + "=" * 60)
    print("[S10] Audit Agent — 审计 (v3)")
    print("=" * 60)

    script = os.path.join(SCRIPT_DIR, "s10_v3_batch_audit.py")
    output_dir = cfg.get("output_dir") or os.path.join(cfg["data_dir"], "AuditContext", cfg["project_name"])
    output_file = cfg.get("audit_output") or os.path.join(cfg["data_dir"], "AuditResult", cfg["project_name"], "audit_report_v3.md")

    if not os.path.isdir(output_dir):
        print(f"  [SKIP] 审计上下文目录不存在: {output_dir}")
        print(f"  请先运行 s9")
        return 1

    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

    cmd = [
        sys.executable, script,
        "--input-dir", output_dir,
        "--output", output_file,
        "--workers", str(cfg.get("workers", DEFAULTS["workers"])),
    ]
    if cfg.get("limit"):
        cmd += ["--limit", str(cfg["limit"])]
    if cfg["api_key"]:
        cmd.append("--api")

    print(f"  Input:   {output_dir}")
    print(f"  Output:  {output_file}")
    print(f"  Workers: {cfg.get('workers', DEFAULTS['workers'])}")

    if cfg["dry_run"]:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return 0

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    print(f"[S10] 完成 (exit={result.returncode})")
    return result.returncode


# ---------------------------------------------------------------------------
# 阶段调度表
# ---------------------------------------------------------------------------
STAGE_RUNNERS = {
    "s1": run_s1,
    "s2": run_s2,
    "s3": run_s3,
    "s4": run_s4,
    "s5": run_s5,
    "s6": run_s6,
    "s6b": run_s6b,
    "s7": run_s7,
    "s8": run_s8,
    "s9": run_s9,
    "s10": run_s10,
}

# 阶段间数据依赖描述
STAGE_PRODUCES = {
    "s1": ["refcount_callgraph.json", "wrapper_stage_traces.json", "CallerInfo/"],
    "s2": ["function_pair_candidates.json"],
    "s3": ["MallocChecker.cpp (已注入)"],
    "s4": ["confirmed_bug_candidates_input.json"],
    "s5": ["judge_results_*.json"],
    "s6": ["smatch_refcount_info.c (已配置)"],
    "s6b": ["auto_cleanup_bugs_*.json"],
    "s7": ["smatch_warns.txt", "refcount_warns.txt"],
    "s8": ["pass2_refcount_warns.txt"],
    "s9": ["审计上下文 .md 文件"],
    "s10": ["audit_report_v3.md"],
}


# =========================================================================
# 主入口
# =========================================================================
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="RefScope — Linux Kernel Refcount Bug Detection Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
流水线范围:
  s1          仅包装器分析
  s1-s5       s1 → s5（包装器分析到报告判定）
  s6-s8       s6 → s8（Smatch 配置到跨函数检测）
  s8-s10      s8 → s10（跨函数检测到审计）
  s1-s10      完整流水线（默认）

示例:
  python3 run_pipeline.py --pipeline s1 --kernel-dir /path/to/linux
  python3 run_pipeline.py --pipeline s6-s8 --data-dir /path/to/data
  python3 run_pipeline.py --pipeline s1-s10 --dry-run
  python3 run_pipeline.py --pipeline s8-s10 --api-key sk-xxx --api-url https://api.xxx.com
        """,
    )

    # ── 流水线控制 ──
    grp_pipe = parser.add_argument_group("流水线控制")
    grp_pipe.add_argument(
        "--pipeline", "--pipe",
        default=DEFAULTS["pipeline"],
        help=f"流水线范围，如 s1, s1-s5, s6-s8, s8-s10, s1-s10（默认: {DEFAULTS['pipeline']}）",
    )
    grp_pipe.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="预览模式：仅打印将执行的命令，不实际运行",
    )
    grp_pipe.add_argument(
        "--stop-on-error",
        action="store_true",
        default=True,
        help="遇到错误时停止流水线（默认开启）",
    )
    grp_pipe.add_argument(
        "--no-stop-on-error",
        action="store_false",
        dest="stop_on_error",
        help="遇到错误继续执行后续阶段",
    )

    # ── 路径配置 ──
    grp_path = parser.add_argument_group("路径配置")
    grp_path.add_argument(
        "--kernel-dir",
        default=DEFAULTS["kernel_dir"],
        help=f"Linux 内核源码目录（默认: {DEFAULTS['kernel_dir']}）",
    )
    grp_path.add_argument(
        "--data-dir",
        default=DEFAULTS["data_dir"],
        help=f"数据共享根目录（默认: {DEFAULTS['data_dir']}）",
    )
    grp_path.add_argument(
        "--smatch-dir",
        default=DEFAULTS["smatch_dir"],
        help=f"Smatch 安装目录（默认: {DEFAULTS['smatch_dir']}）",
    )
    grp_path.add_argument(
        "--function-result-dir",
        default="",
        help=f"FunctionResult 目录（默认: DATA_DIR/FunctionResult/PROJECT_NAME）",
    )
    grp_path.add_argument(
        "--location-info-dir",
        default=DEFAULTS["location_info_dir"],
        help="TargetInfo 目录，包含函数位置信息",
    )
    grp_path.add_argument(
        "--report-dir",
        default="",
        help="Clang 检测报告目录",
    )
    grp_path.add_argument(
        "--project-name",
        default=DEFAULTS["project_name"],
        help=f"项目/运行名称（默认: {DEFAULTS['project_name']}）",
    )
    grp_path.add_argument(
        "--warns-file",
        default="",
        help="s9 输入: Smatch 告警文件路径（自动检测 s8 输出）",
    )
    grp_path.add_argument(
        "--output-dir",
        default="",
        help="s9/s10 输出目录",
    )
    grp_path.add_argument(
        "--audit-output",
        default="",
        help="s10 审计报告输出文件路径",
    )

    # ── API 配置 ──
    grp_api = parser.add_argument_group("API 配置 (LLM)")
    grp_api.add_argument(
        "--api-key",
        default=DEFAULTS["api_key"],
        help="LLM API 密钥（或设置环境变量 ANTHROPIC_API_KEY / DEEPSEEK_API_KEY）",
    )
    grp_api.add_argument(
        "--api-url",
        default=DEFAULTS["api_url"],
        help=f"LLM API 端点 URL（默认: {DEFAULTS['api_url']}）",
    )
    grp_api.add_argument(
        "--model",
        default=DEFAULTS["model"],
        help=f"模型名称（默认: {DEFAULTS['model']}）",
    )
    grp_api.add_argument(
        "--config", "--config-file",
        default=DEFAULTS["config_file"],
        help=f"API 配置文件 .env 格式（默认: {DEFAULTS['config_file']}）",
    )

    # ── 并行与性能 ──
    grp_perf = parser.add_argument_group("并行与性能")
    grp_perf.add_argument(
        "--jobs", "-j",
        type=int,
        default=DEFAULTS["jobs"],
        help=f"Smatch 编译并行数（默认: {DEFAULTS['jobs']}）",
    )
    grp_perf.add_argument(
        "--workers",
        type=int,
        default=DEFAULTS["workers"],
        help=f"审计/判定并行 worker 数（默认: {DEFAULTS['workers']}）",
    )
    grp_perf.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULTS["concurrency"],
        help=f"API 并发数（默认: {DEFAULTS['concurrency']}）",
    )
    grp_perf.add_argument(
        "--limit",
        type=int,
        default=DEFAULTS["limit"],
        help="限制处理条数（0 = 全部）",
    )
    grp_perf.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULTS["max_depth"],
        help=f"s9 被调用者追踪最大深度（默认: {DEFAULTS['max_depth']}）",
    )

    # ── Smatch 配置 ──
    grp_smatch = parser.add_argument_group("Smatch 配置 (s6-s8)")
    grp_smatch.add_argument(
        "--smatch-config",
        choices=["defconfig", "allyesconfig", "skip"],
        default=DEFAULTS["smatch_config"],
        help=f"内核配置模式（默认: {DEFAULTS['smatch_config']}）",
    )
    grp_smatch.add_argument(
        "--skip-config",
        action="store_true",
        help="跳过内核配置步骤（使用已有 .config）",
    )
    grp_smatch.add_argument(
        "--build-smatch",
        action="store_true",
        help="运行前重新编译 Smatch",
    )
    grp_smatch.add_argument(
        "--target-dir",
        default="",
        help="Smatch 扫描的目标子目录（如 drivers/net）",
    )
    grp_smatch.add_argument(
        "--target-file",
        default="",
        help="Smatch 扫描的目标文件（如 net/core/dev.c）",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 构建配置字典
    cfg = {k: v for k, v in DEFAULTS.items()}

    # 从配置文件加载: 优先 api_config.env，回退到 template_api_config.env
    config_path = args.config if hasattr(args, "config") else args.config_file
    if not os.path.exists(config_path):
        # 尝试 api_config.env
        alt = resolve_path("api_config.env")
        if os.path.exists(alt):
            config_path = alt
        else:
            # 回退到模板
            alt = resolve_path("template_api_config.env")
            if os.path.exists(alt):
                config_path = alt
    if os.path.exists(config_path):
        env_config = load_config_file(config_path)
        cfg = merge_config(cfg, env_config)

    # 命令行参数覆盖
    for key, value in vars(args).items():
        if value is not None and key in cfg:
            cfg[key] = value
        elif value is not None:
            cfg[key] = value  # 新参数直接加入

    # 派生目录
    if not cfg.get("function_result_dir"):
        cfg["function_result_dir"] = os.path.join(
            cfg["data_dir"], "FunctionResult", cfg["project_name"]
        )
    if not cfg.get("report_dir"):
        cfg["report_dir"] = os.path.join(
            cfg["data_dir"], "Bug", cfg["project_name"]
        )
    if not cfg.get("smatch_result_base"):
        cfg["smatch_result_base"] = os.path.join(cfg["data_dir"], "SmatchResult")

    # 确保 data_dir 存在
    data_dir = resolve_path(cfg["data_dir"])
    os.makedirs(data_dir, exist_ok=True)
    cfg["data_dir"] = data_dir

    # 解析流水线
    pipeline_spec = cfg.get("pipeline", DEFAULTS["pipeline"])
    stages = parse_pipeline(pipeline_spec)

    # 打印配置摘要
    print("=" * 60)
    print("RefScope Pipeline Runner")
    print("=" * 60)
    print(f"  流水线:     {' → '.join(stages)}")
    print(f"  模式:       {'DRY RUN (预览)' if cfg['dry_run'] else 'LIVE (实际执行)'}")
    print(f"  Kernel:     {cfg['kernel_dir']}")
    print(f"  Data:       {cfg['data_dir']}")
    print(f"  Project:    {cfg['project_name']}")
    print(f"  API URL:    {cfg['api_url']}")
    print(f"  Model:      {cfg['model']}")
    print(f"  Jobs:       {cfg['jobs']}")
    print(f"  Workers:    {cfg['workers']}")
    if cfg.get("target_dir"):
        print(f"  Target dir: {cfg['target_dir']}")
    if cfg.get("target_file"):
        print(f"  Target file: {cfg['target_file']}")
    print()

    # 执行流水线
    start_time = time.time()
    results: Dict[str, int] = {}
    all_passed = True

    for i, stage in enumerate(stages, 1):
        runner = STAGE_RUNNERS.get(stage)
        if runner is None:
            print(f"[WARNING] 未知阶段 '{stage}'，跳过")
            continue

        print(f"\n{'─' * 60}")
        print(f"阶段 {i}/{len(stages)}: {stage}")
        print(f"{'─' * 60}")

        try:
            exit_code = runner(cfg)
            results[stage] = exit_code

            if exit_code != 0:
                print(f"\n[ERROR] {stage} 返回错误码 {exit_code}")
                all_passed = False
                if cfg.get("stop_on_error", True):
                    print("[STOP] 流水线终止（--no-stop-on-error 可跳过错误继续）")
                    break
        except KeyboardInterrupt:
            print(f"\n[INTERRUPTED] 用户在 {stage} 中断执行")
            results[stage] = 130
            all_passed = False
            break
        except Exception as e:
            print(f"\n[EXCEPTION] {stage} 异常: {e}")
            import traceback
            traceback.print_exc()
            results[stage] = -1
            all_passed = False
            if cfg.get("stop_on_error", True):
                break

    # 打印结果摘要
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("流水线执行摘要")
    print("=" * 60)
    for stage, code in results.items():
        status = "✓ OK" if code == 0 else f"✗ FAIL ({code})"
        produces = STAGE_PRODUCES.get(stage, [])
        products_str = f" → {', '.join(produces)}" if produces else ""
        print(f"  {stage}: {status}{products_str}")

    skipped = [s for s in stages if s not in results]
    if skipped:
        print(f"  跳过: {', '.join(skipped)}")

    print(f"\n总耗时: {elapsed:.1f}s")
    print(f"状态:   {'全部通过' if all_passed and not skipped else '有错误/跳过'}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
