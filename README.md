# RefScope — Linux Kernel Refcount Bug Detection Pipeline

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)

RefScope is an LLM-driven pipeline for detecting reference-counting bugs in the Linux kernel. It spans 10 stages (s1–s10): multi-agent wrapper analysis identifies refcount helper functions, builds a call graph, generates get/put pair candidates, configures the Smatch static checker, and performs cross-function auditing.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set required environment variables
export REFCOUNT_KERNEL_DIR=/path/to/linux-kernel
export REFCOUNT_API_KEY=sk-your-api-key

# 3. Run the pipeline
python3 run_pipeline.py --pipeline s1-s5 --dry-run    # preview mode
python3 run_pipeline.py --pipeline s1-s10              # full pipeline
```

## Pipeline Stages

| Stage | File | Description |
|-------|------|-------------|
| s1 | `s1_caller_function_agent.py` | Multi-agent wrapper analysis (judge → extract → check → expand), outputs call graph |
| s2 | `s2_get_function_pairs.py` | Generates get/put pair candidates from the call graph |
| s3 | `s3_rebuild_checker.py` | Injects get/put families into the Clang static checker template |
| s4 | `s4_confirm_bug_candidates.py` | Prepares bug-candidate input for final confirmation |
| s5 | `s5_judge_reports.py` | Judges checker reports with an LLM |
| s6 | `s6_configure_smatch_refcount.py` | Configures Smatch refcount detection rules |
| s6b | `s6b_c_function_parser.py` | C function parser |
| s6b | `s6b_detect_auto_cleanup_bugs.py` | Auto-cleanup bug detection |
| s7 | `s7_run_smatch_refcount.sh` | Runs Smatch intra-procedural refcount scan |
| s8 | `s8_run_smatch_crossfunc.sh` | Runs Smatch cross-function (inter-procedural) scan |
| s9 | `s9_prepare_audit_context.py` | Prepares audit context (extracts function source) |
| s9 | `s9_v2_enrich_context.py` | Enriched audit context (v2) |
| s9 | `s9_v3_contract_context.py` | Contract-driven minimal audit context (v3) |
| s10 | `s10_audit_agent.py` | Iterative audit agent (v1) |
| s10 | `s10_v2_audit_agent.py` | Parallel audit agent (v2) |
| s10 | `s10_v3_batch_audit.py` | Batch audit with contract context (v3) |

## Dependencies (imported by s1–s10)

| File | Purpose |
|------|---------|
| `callgraph.py` | C function call-graph generation (cscope) |
| `accurate_func_locator.py` | Accurate function-definition locator |
| `cross_validator.py` | DWARF + LLM cross-validation of type chains |
| `refcount_primitives.py` | Hard-coded refcount primitive type database |
| `btf_chain_enumerator.py` | BTF type-chain enumerator |

## Template Files

| File | Used By |
|------|---------|
| `template_sys.prompt` | s1 (system prompt) |
| `template_judge.prompt` | s1 (judge stage) |
| `template_extract.prompt` | s1 (extract stage) |
| `template_check.prompt` | s1 (check stage) |
| `template_expand.prompt` | s1 (expand stage) |
| `template_reevaluate.prompt` | s1 (re-evaluate stage) |
| `template_audit_v1.md` | s10 (audit template v1) |
| `template_audit_v2.md` | s10_v2 (audit template v2) |
| `template_audit_v3.md` | s10_v3 (audit template v3) |
| `template_api_config.env` | s10 series (API config template) |

## Requirements

- Python ≥ 3.9
- cscope (for `callgraph.py`)
- bpftool (for `btf_chain_enumerator.py`)
- Smatch static analysis tool (for s7/s8; included under `smatch/`)
- LLM API endpoint (for s1/s5/s10)
- Linux kernel source tree (with `make cscope` configured)

## Configuration

### Required Environment Variables

```bash
export REFCOUNT_KERNEL_DIR=/path/to/linux-kernel   # Linux kernel source directory
export REFCOUNT_API_KEY=sk-your-api-key             # LLM API key
```

### Optional Environment Variables

```bash
export REFCOUNT_DATA_DIR=./data                     # data root (default: ./data, auto-created)
export REFCOUNT_API_URL=https://api.deepseek.com    # API endpoint URL
export REFCOUNT_MODEL=deepseek-v4-flash             # model name
export REFCOUNT_PROJECT_NAME=my-project             # project/run name
export REFCOUNT_CLANG_DIR=/path/to/clang-checker    # Clang checker directory (for s3)
export REFCOUNT_TARGET_INFO_DIR=/path/to/targetinfo # function location info (for s1)
```

### API Config File (Optional)

```bash
cp template_api_config.env api_config.env
# edit api_config.env with your API key and endpoint
# if api_config.env is absent, run_pipeline.py falls back to template_api_config.env
```

## Running Individual Stages

```bash
# s1: wrapper analysis
python3 s1_caller_function_agent.py

# s2: generate pair candidates
python3 s2_get_function_pairs.py

# s3: rebuild checker
python3 s3_rebuild_checker.py

# s4: confirm candidates
python3 s4_confirm_bug_candidates.py

# s5: judge reports
python3 s5_judge_reports.py --report-dir /path/to/reports

# s6: configure Smatch
python3 s6_configure_smatch_refcount.py --dry-run
python3 s6_configure_smatch_refcount.py

# s7: intra-procedural scan
./s7_run_smatch_refcount.sh --target-dir drivers/net

# s8: cross-function scan
./s8_run_smatch_crossfunc.sh --allyesconfig --jobs $(nproc)

# s9 + s10: audit
python3 s9_v3_contract_context.py --warns warns.txt --output-dir ctx/
python3 s10_v3_batch_audit.py --input-dir ctx/ --output report.md --api
```

## Directory Structure

```
RefScope/
├── run_pipeline.py                  # auto-execution script (hyperparameter CLI)
├── README.md                        # this document
├── requirements.txt                 # Python dependencies
├── LICENSE                          # MIT license
│
├── smatch/                          # Smatch static analysis tool (source + binary)
│   ├── smatch                       #   main binary
│   ├── smatch_scripts/              #   helper scripts (gen_*, create_db.sh, etc.)
│   ├── smatch_data/                 #   kernel data files
│   ├── smatch_refcount_info.c       #   refcount detection rules (modified by s6)
│   └── check_*.c                    #   checker modules
│
├── s1_caller_function_agent.py      # Stage 1: wrapper analysis
├── s2_get_function_pairs.py         # Stage 2: pair generation
├── s3_rebuild_checker.py            # Stage 3: checker rebuild
├── s4_confirm_bug_candidates.py     # Stage 4: candidate confirmation
├── s5_judge_reports.py              # Stage 5: report judging
├── s6_configure_smatch_refcount.py  # Stage 6: Smatch configuration
├── s6b_c_function_parser.py         # Stage 6b: C function parser
├── s6b_detect_auto_cleanup_bugs.py  # Stage 6b: auto-cleanup detection
├── s7_run_smatch_refcount.sh        # Stage 7: Smatch intra-procedural scan
├── s8_run_smatch_crossfunc.sh       # Stage 8: Smatch cross-function scan
├── s9_prepare_audit_context.py      # Stage 9: audit context (v1)
├── s9_enrich_context.py             # Stage 9: enriched context
├── s9_contract_context.py           # Stage 9: contract context
├── s10_audit_agent.py               # Stage 10: iterative audit (v1)
├── s10_parallel_audit.py            # Stage 10: parallel audit
├── s10_batch_audit.py               # Stage 10: batch audit
│
├── callgraph.py                     # dependency: call graph
├── accurate_func_locator.py         # dependency: function locator
├── cross_validator.py               # dependency: cross-validation
├── refcount_primitives.py           # dependency: primitive types
├── btf_chain_enumerator.py          # dependency: BTF enumeration
│
├── template_sys.prompt              # template: system prompt
├── template_judge.prompt            # template: judge stage
├── template_extract.prompt          # template: extract stage
├── template_check.prompt            # template: check stage
├── template_expand.prompt           # template: expand stage
├── template_reevaluate.prompt       # template: re-evaluate
├── template_audit_v1.md             # template: audit v1
├── template_audit_v2.md             # template: audit v2
├── template_audit_v3.md             # template: audit v3
└── template_api_config.env          # template: API config
```

## Data Directory

The pipeline reads from and writes to a shared data directory (`REFCOUNT_DATA_DIR`, default `./data`). A pre-populated dataset is available under `/home/liang/workspace/Bak/data/` with the following structure:

```
data/
├── bug_reports/                         # Bug reports confirmed as real by LLM audit
│   └── *.json                           #   per-function confirmed bug reports (s10 output)
│
├── checker_warns/                       # Raw checker warnings (Smatch + auto-cleanup)
│   ├── smatch/                          #   Smatch intra- & cross-function refcount warnings
│   └── auto_cleanup/                    #   s6b auto-cleanup bug detection warnings
│
├── comparision_study/                   # Comparison study: APISpecGen vs RefScope
│   └── APISpecGen_deepth*.json          #   APISpecGen reports at various depths
│
└── wrapper_identification_reports/      # Wrapper function identification results (s1 output)
    ├── refcount_callgraph.json          #   full refcount call graph
    ├── wrapper_stage_traces.json        #   per-stage agent traces for debugging
    └── function_pair_candidates.json    #   get/put pair candidates (s2 output)
```

| Subdirectory | Description | Produced By |
|-------------|-------------|-------------|
| `bug_reports/` | LLM-confirmed real refcount bugs | s10 (audit) |
| `checker_warns/` | Raw Smatch & auto-cleanup detector warnings | s6b, s7, s8 |
| `comparision_study/` | Comparison-study reports (APISpecGen baseline) | external |
| `wrapper_identification_reports/` | Wrapper function analysis & pair candidates | s1, s2 |
| `FunctionResult/` | Per-function type-chain & contract analysis | s1 |
| `SmatchResult/` | Timestamped Smatch scan outputs | s7, s8 |

## CLI Reference (`run_pipeline.py`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--pipeline` | str | `s1-s10` | pipeline range: `s1`, `s1-s5`, `s6-s8`, `s8-s10`, `s1-s10` |
| `--kernel-dir` | path | env `REFCOUNT_KERNEL_DIR` | Linux kernel source directory |
| `--data-dir` | path | `./data` | shared data root directory |
| `--smatch-dir` | path | `./smatch` | Smatch installation directory |
| `--api-key` | str | env `REFCOUNT_API_KEY` | LLM API key |
| `--api-url` | str | `https://api.deepseek.com` | LLM API endpoint URL |
| `--model` | str | `deepseek-v4-flash` | LLM model name |
| `--jobs` | int | `$(nproc)` | parallel build jobs for Smatch |
| `--workers` | int | `4` | parallel audit/LLM workers |
| `--limit` | int | `0` | limit items processed (0 = all) |
| `--dry-run` | flag | `false` | preview mode — print commands without executing |
| `--config` | path | `api_config.env` | API config file (`.env` format) |
| `--target-dir` | str | `""` | Smatch scan target subdirectory (e.g. `drivers/net`) |
| `--build-smatch` | flag | `false` | rebuild Smatch before scanning |
