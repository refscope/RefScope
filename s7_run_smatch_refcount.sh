#!/bin/bash
#
# s7_run_smatch_refcount.sh — 运行 smatch 引用计数检测并收集结果
#
# Usage:
#   ./s7_run_smatch_refcount.sh                          # 默认: defconfig + 全量编译
#   ./s7_run_smatch_refcount.sh --target-dir drivers/net  # 仅扫描指定子目录
#   ./s7_run_smatch_refcount.sh --skip-config             # 跳过内核配置 (已有 .config)
#   ./s7_run_smatch_refcount.sh --allyesconfig            # 使用 allyesconfig
#   ./s7_run_smatch_refcount.sh --jobs 32                 # 并行编译数
#   ./s7_run_smatch_refcount.sh --allyesconfig --build-smatch --jobs 96 # 常用配置
#
# Output:
#   result/YYYYMMDD_HHMMSS/smatch_warns.txt     # 原始全部告警
#   result/YYYYMMDD_HHMMSS/refcount_warns.txt   # refcount 专属告警
#   result/YYYYMMDD_HHMMSS/summary.json          # 统计摘要

set -euo pipefail

# ============================================================================
# 路径配置
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SMATCH_BIN="${SMATCH_BIN:-$SCRIPT_DIR/smatch/smatch}"
SMATCH_SRC_DIR="${SMATCH_SRC_DIR:-$SCRIPT_DIR/smatch}"
KERNEL_DIR="${KERNEL_DIR:-}"
RESULT_BASE="${RESULT_BASE:-$SCRIPT_DIR/result}"

# ============================================================================
# 默认参数
# ============================================================================
CONFIG_MODE="defconfig"   # defconfig | allyesconfig | skip
SMATCH_ENABLE="check_refcount_inconsistent_returns"
JOBS=$(nproc)
TARGET_DIR=""             # 空 = 全量, 否则只编译指定子目录
BUILD_SMATCH=0            # 是否在运行前编译 smatch

# ============================================================================
# 参数解析
# ============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --defconfig        使用 defconfig 配置内核 (默认)
  --allyesconfig     使用 allyesconfig 配置内核
  --skip-config      跳过内核配置步骤 (使用已有 .config)
  --jobs N           并行编译任务数 (默认: $(nproc))
  --target-dir DIR   仅扫描指定子目录 (如 drivers/net, net/core)
  --target-file FILE 仅扫描指定文件
  --checks CHECKS    启用的检查器, 逗号分隔 (默认: $SMATCH_ENABLE)
  --output-dir DIR   输出目录 (默认: $RESULT_BASE/<timestamp>)
  --build-log FILE   编译日志路径 (默认: 输出目录下的 build.log)
  --build-smatch     运行前先编译 smatch (推荐在 s6 之后使用)
  --dry-run          仅打印将要执行的命令, 不实际运行
  --help             显示此帮助
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --defconfig)       CONFIG_MODE="defconfig"; shift ;;
        --allyesconfig)    CONFIG_MODE="allyesconfig"; shift ;;
        --skip-config)     CONFIG_MODE="skip"; shift ;;
        --jobs)            JOBS="$2"; shift 2 ;;
        --target-dir)      TARGET_DIR="$2"; shift 2 ;;
        --target-file)     TARGET_FILE="$2"; shift 2 ;;
        --checks)          SMATCH_ENABLE="$2"; shift 2 ;;
        --output-dir)      RESULT_DIR="$2"; shift 2 ;;
        --build-log)       BUILD_LOG="$2"; shift 2 ;;
        --build-smatch)    BUILD_SMATCH=1; shift ;;
        --dry-run)         DRY_RUN=1; shift ;;
        --help)            usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# ============================================================================
# 初始化
# ============================================================================
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_DIR="${RESULT_DIR:-$RESULT_BASE/$TIMESTAMP}"
BUILD_LOG="${BUILD_LOG:-$RESULT_DIR/build.log}"
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$RESULT_DIR"

# ============================================================================
# 前置检查
# ============================================================================
check_prerequisites() {
    local missing=()

    if [[ ! -x "$SMATCH_BIN" ]]; then
        missing+=("smatch binary: $SMATCH_BIN")
    fi

    # 检查 smatch_refcount_info.c 是否比二进制更新（s6 之后未重新编译）
    local info_c="$SMATCH_SRC_DIR/smatch_refcount_info.c"
    if [[ -x "$SMATCH_BIN" ]] && [[ -f "$info_c" ]]; then
        if [[ "$info_c" -nt "$SMATCH_BIN" ]]; then
            if [[ "$BUILD_SMATCH" -eq 1 ]]; then
                echo "[WARN] smatch_refcount_info.c is newer than binary (will rebuild)"
            else
                echo "ERROR: smatch_refcount_info.c is newer than smatch binary!"
                echo "  Source: $info_c"
                echo "  Binary: $SMATCH_BIN"
                echo ""
                echo "  The binary was not rebuilt after s6 configured new functions."
                echo "  Either:"
                echo "    1. Re-run with --build-smatch to auto-rebuild"
                echo "    2. Manually: cd $SMATCH_SRC_DIR && make"
                exit 1
            fi
        fi
    fi

    if [[ ! -d "$KERNEL_DIR" ]]; then
        missing+=("kernel directory: $KERNEL_DIR")
    fi
    if [[ ! -f "$KERNEL_DIR/Makefile" ]]; then
        missing+=("kernel Makefile")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: Missing prerequisites:"
        for m in "${missing[@]}"; do
            echo "  - $m"
        done
        exit 1
    fi

    echo "[OK] smatch binary: $SMATCH_BIN"
    echo "[OK] kernel directory: $KERNEL_DIR"
    echo "[OK] result directory: $RESULT_DIR"
}

# ============================================================================
# 编译 smatch
# ============================================================================
build_smatch() {
    local info_c="$SMATCH_SRC_DIR/smatch_refcount_info.c"

    echo "=== Step 0: Build smatch ==="
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] make -C $SMATCH_SRC_DIR"
        return
    fi

    if [[ ! -d "$SMATCH_SRC_DIR" ]]; then
        echo "ERROR: smatch source directory not found: $SMATCH_SRC_DIR"
        exit 1
    fi
    if [[ ! -f "$SMATCH_SRC_DIR/Makefile" ]]; then
        echo "ERROR: smatch Makefile not found in $SMATCH_SRC_DIR"
        exit 1
    fi

    echo "Building smatch..."
    make -C "$SMATCH_SRC_DIR" -j"$(nproc)"
    echo "[OK] smatch build complete"
    echo "  Binary: $SMATCH_BIN"
    echo "  Built:  $(stat -c %y "$SMATCH_BIN" 2>/dev/null || date)"
}

# ============================================================================
# 内核配置
# ============================================================================
configure_kernel() {
    case "$CONFIG_MODE" in
        defconfig)
            echo "=== Step 1: make defconfig ==="
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "[DRY RUN] make -C $KERNEL_DIR defconfig"
            else
                make -C "$KERNEL_DIR" defconfig
                echo "[OK] defconfig done"
            fi
            ;;
        allyesconfig)
            echo "=== Step 1: make allyesconfig (this enables ALL drivers, build may take hours) ==="
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "[DRY RUN] make -C $KERNEL_DIR allyesconfig"
            else
                make -C "$KERNEL_DIR" allyesconfig
                echo "[OK] allyesconfig done"
            fi
            ;;
        skip)
            if [[ ! -f "$KERNEL_DIR/.config" ]]; then
                echo "ERROR: --skip-config specified but $KERNEL_DIR/.config not found"
                exit 1
            fi
            echo "=== Step 1: skip config (using existing .config) ==="
            ;;
    esac
}

# ============================================================================
# 构建 SMATCH_CHECK 命令
# ============================================================================
build_check_cmd() {
    local cmd="$SMATCH_BIN -p=kernel --file-output --succeed --info"
    if [[ -n "$SMATCH_ENABLE" ]]; then
        cmd="$cmd --enable=$SMATCH_ENABLE"
    fi
    echo "$cmd"
}

# ============================================================================
# 运行 smatch
# ============================================================================
run_smatch() {
    local check_cmd
    check_cmd=$(build_check_cmd)

    local make_target=""
    local make_args=(-C "$KERNEL_DIR" -j"$JOBS" -k)

    if [[ -n "${TARGET_FILE:-}" ]]; then
        make_args+=("$TARGET_FILE")
    elif [[ -n "$TARGET_DIR" ]]; then
        make_args+=("$TARGET_DIR")
    fi

    echo "=== Step 2: Run smatch ==="
    echo "  CHECK:  $check_cmd"
    echo "  Target: ${TARGET_FILE:-${TARGET_DIR:-all}}"
    echo "  Jobs:   $JOBS"
    echo "  Log:    $BUILD_LOG"
    echo ""

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] make ${make_args[*]} CHECK=\"$check_cmd\" C=2"
        return
    fi

    # 清理旧的构建产物和 smatch 输出
    echo "[Clean] make clean (kernel)..."
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] make -C $KERNEL_DIR clean"
    else
        make -C "$KERNEL_DIR" clean 2>&1 | tail -1
    fi

    echo "[Clean] Removing stale .c.smatch files..."
    find "$KERNEL_DIR" -name '*.c.smatch' -delete 2>/dev/null || true

    # 运行编译+检查, 使用 C=2 强制检查所有文件, -k 确保遇到错误也继续
    local start_ts
    start_ts=$(date +%s)

    make "${make_args[@]}" \
        CHECK="$check_cmd" \
        C=2 2>&1 | tee "$BUILD_LOG"

    local build_rc=${PIPESTATUS[0]}
    local end_ts
    end_ts=$(date +%s)
    local elapsed=$((end_ts - start_ts))

    echo ""
    echo "Build exit code: $build_rc"
    echo "Elapsed: ${elapsed}s"

    # 返回码 0=成功, 2=有编译错误但部分成功（-k 模式常见）
    if [[ $build_rc -eq 0 ]] || [[ $build_rc -eq 2 ]]; then
        echo "[OK] Smatch scan completed"
    else
        echo "[WARN] Build had errors (exit code: $build_rc), collecting partial results..."
    fi
}

# ============================================================================
# 收集结果
# ============================================================================
collect_results() {
    echo ""
    echo "=== Step 3: Collect results ==="

    local raw_warns="$RESULT_DIR/smatch_warns.txt"
    local refcount_warns="$RESULT_DIR/refcount_warns.txt"
    local summary_json="$RESULT_DIR/summary.json"

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] find $KERNEL_DIR -name '*.c.smatch' -exec cat {} \\; > $raw_warns"
        echo "[DRY RUN] grep refcount + inconsistent patterns → $refcount_warns"
        return
    fi

    # 收集所有 .c.smatch 文件
    echo "Collecting .c.smatch files..."
    find "$KERNEL_DIR" -name '*.c.smatch' -exec cat {} \; > "$raw_warns" 2>/dev/null || true

    local total_lines
    total_lines=$(wc -l < "$raw_warns" 2>/dev/null || echo 0)

    # 过滤 refcount 相关告警
    echo "Filtering refcount warnings..."
    {
        echo "# Smatch Refcount Warnings (Negative Samples)"
        echo "# Generated: $(date)"
        echo "# Kernel: $KERNEL_DIR"
        echo "# Smatch enable: $SMATCH_ENABLE"
        echo "#"
        echo ""
        grep -nE "warn: (inconsistent refcounting|refcount leak|refcount false put)" "$raw_warns" 2>/dev/null || echo "# No refcount warnings found."
    } > "$refcount_warns"

    local refcount_count
    refcount_count=$(grep -cE "warn: (inconsistent refcounting|refcount leak|refcount false put)" "$raw_warns" 2>/dev/null | tr -d '\n' || echo 0)
    refcount_count=${refcount_count:-0}

    # 提取正样例: 路径上 get/put 平衡的 refcount 操作
    local balanced_warns="$RESULT_DIR/balanced_refcount.txt"
    echo "Extracting positive samples (balanced refcount)..."
    {
        echo "# Smatch Balanced Refcount (Positive Samples)"
        echo "# Generated: $(date)"
        echo "# Kernel: $KERNEL_DIR"
        echo "# Each line: file:line function() info: balanced refcount 'var': line=N inc=[get_fn,...] dec=[put_fn,...]"
        echo "#"
        echo ""
        grep -nE "info: balanced refcount" "$raw_warns" 2>/dev/null || echo "# No balanced refcount found."
    } > "$balanced_warns"

    local balanced_count
    balanced_count=$(grep -cE "info: balanced refcount" "$raw_warns" 2>/dev/null | tr -d '\n' || echo 0)
    balanced_count=${balanced_count:-0}


    # 同时收集 kernel 中 register_ 的 info 输出
    local info_count=0
    if grep -q "warn:" "$raw_warns" 2>/dev/null; then
        info_count=$(grep -c "warn:" "$raw_warns" 2>/dev/null || echo 0)
    fi

    # 生成摘要
    cat > "$summary_json" <<JSONEOF
{
  "timestamp": "$TIMESTAMP",
  "kernel": "$KERNEL_DIR",
  "smatch_bin": "$SMATCH_BIN",
  "smatch_enable": "$SMATCH_ENABLE",
  "config_mode": "$CONFIG_MODE",
  "jobs": $JOBS,
  "target": "${TARGET_DIR:-${TARGET_FILE:-all}}",
  "total_warnings": $total_lines,
  "refcount_warnings": $refcount_count,
  "output_files": {
    "raw_warns": "$raw_warns",
    "refcount_warns": "$refcount_warns",
    "build_log": "$BUILD_LOG"
  }
}
JSONEOF

    echo ""
    echo "============================================"
    echo "  Results Summary"
    echo "============================================"
    echo "  Total smatch lines : $total_lines"
    echo "  Refcount warnings  : $refcount_count"
    echo "  Raw warns          : $raw_warns"
    echo "  Refcount warns     : $refcount_warns"
    echo "  Build log          : $BUILD_LOG"
    echo "  Summary            : $summary_json"
    echo "============================================"

    if [[ "$refcount_count" -gt 0 ]]; then
        echo ""
        echo "--- Refcount Warnings Preview (first 20) ---"
        head -20 "$refcount_warns"
    fi
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo "============================================"
    echo "  s7: Smatch Refcount Detector"
    echo "  $(date)"
    echo "============================================"
    echo ""

    check_prerequisites
    if [[ "$BUILD_SMATCH" -eq 1 ]]; then
        build_smatch
    fi
    configure_kernel
    run_smatch
    collect_results

    echo ""
    echo "Done."
}

main
