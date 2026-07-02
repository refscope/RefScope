#!/bin/bash
#
# s8_run_smatch_crossfunc.sh — smatch 过程间 (cross-function) 引用计数检测
#
# 与 s7 的区别: s7 仅做单遍函数内分析; s8 通过 --call-tree + --info + 建库 +
# 第二遍扫描, 实现跨函数/跨文件的引用计数追踪。
#
# 工作流:
#   Pass 1: smatch --info --call-tree --spammy  → 收集调用关系与函数签名
#   Build DB: 运行 gen_* 脚本 + create_db.sh    → 构建 smatch_db.sqlite
#   Pass 2: smatch (with DB)                     → 带跨函数信息重新检查
#
# Usage:
#   ./s8_run_smatch_crossfunc.sh                              # 默认: defconfig + 全量
#   ./s8_run_smatch_crossfunc.sh --target-dir drivers/net      # 仅扫描指定子目录
#   ./s8_run_smatch_crossfunc.sh --skip-config                 # 跳过内核配置
#   ./s8_run_smatch_crossfunc.sh --pass1-only                  # 仅执行 Pass 1 + 建库
#   ./s8_run_smatch_crossfunc.sh --pass2-only                  # 基于已有 DB 仅执行 Pass 2
#   ./s8_run_smatch_crossfunc.sh --jobs 32                     # 并行编译数
#   ./s8_run_smatch_crossfunc.sh --build-smatch                # 运行前先编译 smatch
#   ./s8_run_smatch_crossfunc.sh --dry-run                     # 仅打印命令
#
# Output:
#   result/YYYYMMDD_HHMMSS/pass1_warns.txt          # Pass 1 原始告警
#   result/YYYYMMDD_HHMMSS/pass1_warns.txt.sql       # Pass 1 SQL 数据
#   result/YYYYMMDD_HHMMSS/pass1_warns.txt.caller_info # Pass 1 调用者信息
#   result/YYYYMMDD_HHMMSS/pass2_warns.txt           # Pass 2 告警 (含跨函数)
#   result/YYYYMMDD_HHMMSS/pass2_refcount_warns.txt  # Pass 2 refcount 专属告警
#   result/YYYYMMDD_HHMMSS/summary.json               # 统计摘要

set -euo pipefail

# ============================================================================
# 路径配置
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SMATCH_BIN="${SMATCH_BIN:-$SCRIPT_DIR/smatch/smatch}"
SMATCH_SRC_DIR="${SMATCH_SRC_DIR:-$SCRIPT_DIR/smatch}"
SMATCH_SCRIPTS_DIR="$SMATCH_SRC_DIR/smatch_scripts"
SMATCH_DATA_DIR="$SMATCH_SRC_DIR/smatch_data"
KERNEL_DIR="${KERNEL_DIR:-}"
RESULT_BASE="${RESULT_BASE:-$SCRIPT_DIR/result}"

# ============================================================================
# 默认参数
# ============================================================================
CONFIG_MODE="allyesconfig"
SMATCH_ENABLE="check_refcount_inconsistent_returns,check_refcount_uaf"
JOBS=$(nproc)
TARGET_DIR=""
TARGET_FILE=""
BUILD_SMATCH=0
DRY_RUN=0
PASS1_ONLY=0
PASS2_ONLY=0
RESULT_DIR=""
BUILD_LOG=""

# ============================================================================
# 参数解析
# ============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

s8: smatch 过程间 (cross-function) 引用计数检测

Options:
  --defconfig        使用 defconfig 配置内核 (默认)
  --allyesconfig     使用 allyesconfig 配置内核
  --skip-config      跳过内核配置步骤
  --jobs N           并行编译任务数 (默认: $(nproc))
  --target-dir DIR   仅扫描指定子目录
  --target-file FILE 仅扫描指定文件
  --checks CHECKS    启用的检查器 (默认: $SMATCH_ENABLE)
  --output-dir DIR   输出目录 (默认: $RESULT_BASE/<timestamp>)
  --build-smatch     运行前先编译 smatch
  --pass1-only       仅执行 Pass 1 (info + call-tree) + 建库, 跳过 Pass 2
  --pass2-only       基于已有 DB 仅执行 Pass 2
  --dry-run          仅打印将要执行的命令
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
        --build-smatch)    BUILD_SMATCH=1; shift ;;
        --pass1-only)      PASS1_ONLY=1; shift ;;
        --pass2-only)      PASS2_ONLY=1; shift ;;
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
    if [[ ! -d "$KERNEL_DIR" ]]; then
        missing+=("kernel directory: $KERNEL_DIR")
    fi
    if [[ ! -f "$KERNEL_DIR/Makefile" ]]; then
        missing+=("kernel Makefile")
    fi
    if [[ ! -d "$SMATCH_SCRIPTS_DIR" ]]; then
        missing+=("smatch scripts: $SMATCH_SCRIPTS_DIR")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: Missing prerequisites:"
        for m in "${missing[@]}"; do
            echo "  - $m"
        done
        exit 1
    fi

    echo "[OK] smatch binary    : $SMATCH_BIN"
    echo "[OK] smatch scripts   : $SMATCH_SCRIPTS_DIR"
    echo "[OK] kernel directory : $KERNEL_DIR"
    echo "[OK] result directory : $RESULT_DIR"
}

# ============================================================================
# 编译 smatch
# ============================================================================
build_smatch() {
    echo "=== Step 0: Build smatch ==="
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] make -C $SMATCH_SRC_DIR -j$(nproc)"
        return
    fi
    make -C "$SMATCH_SRC_DIR" -j"$(nproc)"
    echo "[OK] smatch build complete"
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
            echo "=== Step 1: make allyesconfig ==="
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "[DRY RUN] make -C $KERNEL_DIR allyesconfig"
            else
                make -C "$KERNEL_DIR" allyesconfig
                echo "[OK] allyesconfig done"
            fi
            ;;
        skip)
            if [[ ! -f "$KERNEL_DIR/.config" ]]; then
                echo "ERROR: --skip-config but $KERNEL_DIR/.config not found"
                exit 1
            fi
            echo "=== Step 1: skip config ==="
            ;;
    esac
}

# ============================================================================
# 构建 smatch CHECK 命令
# ============================================================================
build_check_cmd_base() {
    local cmd="$SMATCH_BIN -p=kernel --file-output --succeed"
    if [[ -n "$SMATCH_ENABLE" ]]; then
        cmd="$cmd --enable=$SMATCH_ENABLE"
    fi
    echo "$cmd"
}

# ============================================================================
# Pass 1: Info pass — 收集跨函数数据
# ============================================================================
run_pass1() {
    echo ""
    echo "============================================"
    echo "  Pass 1: Info + Call-tree Collection"
    echo "  $(date)"
    echo "============================================"
    echo ""

    local base_cmd
    base_cmd=$(build_check_cmd_base)
    local check_cmd="$base_cmd --info --call-tree --spammy"

    local make_args=(-C "$KERNEL_DIR" -j"$JOBS" -k)

    if [[ -n "${TARGET_FILE:-}" ]]; then
        make_args+=("$TARGET_FILE")
    elif [[ -n "$TARGET_DIR" ]]; then
        make_args+=("$TARGET_DIR")
    fi

    echo "  CHECK:  $check_cmd"
    echo "  Target: ${TARGET_FILE:-${TARGET_DIR:-all}}"
    echo "  Jobs:   $JOBS"
    echo ""

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] make ${make_args[*]} CHECK=\"$check_cmd\" C=1"
        echo "[DRY RUN] collect .c.smatch → pass1_warns.txt"
        echo "[DRY RUN] collect .c.smatch.sql → pass1_warns.txt.sql"
        echo "[DRY RUN] collect .c.smatch.caller_info → pass1_warns.txt.caller_info"
        return
    fi

    # 清理旧的构建产物和 smatch 输出
    echo "[Clean] make clean..."
    make -C "$KERNEL_DIR" clean 2>&1 | tail -1

    echo "[Clean] Removing stale smatch and object files..."
    find "$KERNEL_DIR" -name '*.c.smatch' -delete 2>/dev/null || true
    find "$KERNEL_DIR" -name '*.c.smatch.sql' -delete 2>/dev/null || true
    find "$KERNEL_DIR" -name '*.c.smatch.caller_info' -delete 2>/dev/null || true
    # 强制删除目标目录下的 .o 文件, 确保 make 会重新编译
    if [[ -n "${TARGET_FILE:-}" ]]; then
        rm -f "$KERNEL_DIR/${TARGET_FILE%.c}.o" 2>/dev/null || true
    elif [[ -n "$TARGET_DIR" ]]; then
        find "$KERNEL_DIR/$TARGET_DIR" -name '*.o' -delete 2>/dev/null || true
    fi

    # 删除旧的数据库 (确保用新数据构建)
    rm -f "$KERNEL_DIR/smatch_db.sqlite" "$KERNEL_DIR/smatch_db.sqlite.new"

    # 运行编译+检查, C=1 检查所有编译的文件
    local start_ts
    start_ts=$(date +%s)

    local pass1_log="$RESULT_DIR/pass1_build.log"
    make "${make_args[@]}" \
        CHECK="$check_cmd" \
        C=1 2>&1 | tee "$pass1_log" || true

    local build_rc=${PIPESTATUS[0]}
    local end_ts
    end_ts=$(date +%s)
    local elapsed=$((end_ts - start_ts))

    echo ""
    echo "Pass 1 exit code: $build_rc"
    echo "Elapsed: ${elapsed}s"

    # 收集输出
    local pass1_warns="$RESULT_DIR/pass1_warns.txt"
    echo "[Collect] .c.smatch → $pass1_warns"
    find "$KERNEL_DIR" -name '*.c.smatch' -exec cat {} \; > "$pass1_warns" 2>/dev/null || true
    local total_lines
    total_lines=$(wc -l < "$pass1_warns" 2>/dev/null || echo 0)
    echo "  Total warns: $total_lines"

    # 收集 SQL 和 caller_info
    local pass1_sql="$RESULT_DIR/pass1_warns.txt.sql"
    local pass1_ci="$RESULT_DIR/pass1_warns.txt.caller_info"

    find "$KERNEL_DIR" -name '*.c.smatch.sql' -exec cat {} \; > "$pass1_sql" 2>/dev/null || true
    find "$KERNEL_DIR" -name '*.c.smatch.caller_info' -exec cat {} \; > "$pass1_ci" 2>/dev/null || true

    echo "  SQL lines: $(wc -l < "$pass1_sql" 2>/dev/null || echo 0)"
    echo "  Caller_info lines: $(wc -l < "$pass1_ci" 2>/dev/null || echo 0)"

    # 把 sql 和 caller_info 复制到 kernel 目录供 create_db.sh 使用
    cp "$pass1_sql" "$KERNEL_DIR/smatch_warns.txt.sql"
    cp "$pass1_ci" "$KERNEL_DIR/smatch_warns.txt.caller_info"
    cp "$pass1_warns" "$KERNEL_DIR/smatch_warns.txt"

    echo "[OK] Pass 1 complete"
}

# ============================================================================
# Build Database — 从 Pass 1 数据构建 smatch_db.sqlite
# ============================================================================
build_database() {
    echo ""
    echo "============================================"
    echo "  Build Cross-Function Database"
    echo "  $(date)"
    echo "============================================"
    echo ""

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] cd $KERNEL_DIR"
        echo "[DRY RUN] run gen_* scripts against pass1_warns.txt"
        echo "[DRY RUN] create_db.sh -p=kernel pass1_warns.txt"
        return
    fi

    local warns_file="$KERNEL_DIR/smatch_warns.txt"
    if [[ ! -f "$warns_file" ]]; then
        echo "ERROR: pass1_warns.txt not found at $warns_file"
        exit 1
    fi

    local start_ts
    start_ts=$(date +%s)

    (
        cd "$KERNEL_DIR"

        # 1. 运行 gen_* 脚本生成 kernel.* 项目数据
        echo "[Gen] Running gen_* scripts..."
        for script in "$SMATCH_SCRIPTS_DIR"/gen_*.sh; do
            echo "  $(basename "$script")"
            "$script" smatch_warns.txt -p=kernel 2>/dev/null || true
        done

        # 移动生成的 kernel.* 文件到 smatch_data
        echo "[Move] kernel.* → $SMATCH_DATA_DIR"
        mv -f kernel.* "$SMATCH_DATA_DIR/" 2>/dev/null || true

        # 2. 构建数据库
        echo "[DB] Creating smatch_db.sqlite..."
        "$SMATCH_DATA_DIR/db/create_db.sh" -p=kernel smatch_warns.txt

        if [[ -f smatch_db.sqlite ]]; then
            local db_size
            db_size=$(du -h smatch_db.sqlite | cut -f1)
            echo "[OK] Database created: smatch_db.sqlite ($db_size)"
        else
            echo "[ERROR] Database creation failed!"
            exit 1
        fi
    )

    local end_ts
    end_ts=$(date +%s)
    echo "Database build elapsed: $((end_ts - start_ts))s"

    # 复制数据库到结果目录
    cp "$KERNEL_DIR/smatch_db.sqlite" "$RESULT_DIR/"
    echo "[OK] Database copied to $RESULT_DIR/"
}

# ============================================================================
# Pass 2: 使用数据库进行跨函数检查
# ============================================================================
run_pass2() {
    echo ""
    echo "============================================"
    echo "  Pass 2: Cross-Function Analysis (with DB)"
    echo "  $(date)"
    echo "============================================"
    echo ""

    if [[ ! -f "$KERNEL_DIR/smatch_db.sqlite" ]]; then
        echo "ERROR: smatch_db.sqlite not found in $KERNEL_DIR"
        echo "  Run --pass1-only first, or provide an existing database."
        exit 1
    fi

    local base_cmd
    base_cmd=$(build_check_cmd_base)
    local check_cmd="$base_cmd --info"

    local make_args=(-C "$KERNEL_DIR" -j"$JOBS" -k)

    if [[ -n "${TARGET_FILE:-}" ]]; then
        make_args+=("$TARGET_FILE")
    elif [[ -n "$TARGET_DIR" ]]; then
        make_args+=("$TARGET_DIR")
    fi

    echo "  CHECK:  $check_cmd"
    echo "  Target: ${TARGET_FILE:-${TARGET_DIR:-all}}"
    echo "  Jobs:   $JOBS"
    echo ""

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] make ${make_args[*]} CHECK=\"$check_cmd\" C=1"
        return
    fi

    # 清理旧的 smatch 输出和 .o 文件, 强制重新编译
    # 保留 smatch_db.sqlite, 仅清理编译产物
    echo "[Clean] make clean (preserving DB)..."
    make -C "$KERNEL_DIR" clean 2>&1 | tail -1 || true
    echo "[Clean] Removing stale Pass 2 smatch files..."
    find "$KERNEL_DIR" -name '*.c.smatch' -delete 2>/dev/null || true

    local start_ts
    start_ts=$(date +%s)

    local pass2_log="$RESULT_DIR/pass2_build.log"
    make "${make_args[@]}" \
        CHECK="$check_cmd" \
        C=1 2>&1 | tee "$pass2_log" || true

    local build_rc=${PIPESTATUS[0]}
    local end_ts
    end_ts=$(date +%s)
    local elapsed=$((end_ts - start_ts))

    echo ""
    echo "Pass 2 exit code: $build_rc"
    echo "Elapsed: ${elapsed}s"

    # 收集 Pass 2 输出
    local pass2_warns="$RESULT_DIR/pass2_warns.txt"
    find "$KERNEL_DIR" -name '*.c.smatch' -exec cat {} \; > "$pass2_warns" 2>/dev/null || true

    local total_lines
    total_lines=$(wc -l < "$pass2_warns" 2>/dev/null || echo 0)
    echo "  Total warns: $total_lines"

    echo "[OK] Pass 2 complete"
}

# ============================================================================
# 收集结果 & 对比 Pass 1 vs Pass 2
# ============================================================================
collect_and_compare() {
    echo ""
    echo "============================================"
    echo "  Collect & Compare Results"
    echo "============================================"
    echo ""

    local pass1_warns="$RESULT_DIR/pass1_warns.txt"
    local pass2_warns="$RESULT_DIR/pass2_warns.txt"

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[DRY RUN] Compare pass1 vs pass2 refcount warnings..."
        return
    fi

    # 提取 refcount 告警 (leak + excess put + inconsistent)
    local REFCOUNT_PATTERN="inconsistent refcounting|refcount leak|refcount excess put"
    local pass1_refcount="$RESULT_DIR/pass1_refcount_warns.txt"
    local pass2_refcount="$RESULT_DIR/pass2_refcount_warns.txt"

    {
        echo "# Smatch Pass 1 Refcount Warnings (intra-procedural only)"
        echo "# Generated: $(date)"
        echo "#"
        echo ""
        grep -nE "$REFCOUNT_PATTERN" "$pass1_warns" 2>/dev/null || echo "# No refcount warnings found."
    } > "$pass1_refcount"

    {
        echo "# Smatch Pass 2 Refcount Warnings (with cross-function analysis)"
        echo "# Generated: $(date)"
        echo "#"
        echo ""
        grep -nE "$REFCOUNT_PATTERN" "$pass2_warns" 2>/dev/null || echo "# No refcount warnings found."
    } > "$pass2_refcount"

    local p1_count
    p1_count=$(grep -cE "$REFCOUNT_PATTERN" "$pass1_warns" 2>/dev/null || echo 0)
    local p2_count
    p2_count=$(grep -cE "$REFCOUNT_PATTERN" "$pass2_warns" 2>/dev/null || echo 0)

    # 提取 UAF 告警
    local UAF_PATTERN="after refcount release|after possible refcount release"
    local pass1_uaf="$RESULT_DIR/pass1_uaf_warns.txt"
    local pass2_uaf="$RESULT_DIR/pass2_uaf_warns.txt"

    grep -nE "$UAF_PATTERN" "$pass1_warns" 2>/dev/null > "$pass1_uaf" || true
    grep -nE "$UAF_PATTERN" "$pass2_warns" 2>/dev/null > "$pass2_uaf" || true
    local p1_uaf=$(wc -l < "$pass1_uaf" 2>/dev/null || echo 0)
    local p2_uaf=$(wc -l < "$pass2_uaf" 2>/dev/null || echo 0)

    # 提取 must_check 告警
    local MC_PATTERN="not checked.*must_check"
    local pass2_mc="$RESULT_DIR/pass2_must_check_warns.txt"
    grep -nE "$MC_PATTERN" "$pass2_warns" 2>/dev/null > "$pass2_mc" || true
    local p2_mc=$(wc -l < "$pass2_mc" 2>/dev/null || echo 0)

    # 计算 Pass 2 独有的告警 (跨函数新发现的)
    local p2_only="$RESULT_DIR/pass2_only_refcount_warns.txt"
    if [[ -f "$pass1_warns" ]] && [[ -f "$pass2_warns" ]]; then
        # 提取告警签名 (去掉行号前缀)
        grep -E "warn: ($REFCOUNT_PATTERN)" "$pass1_warns" 2>/dev/null | \
            sed 's/^[0-9]\+://' | sort -u > /tmp/_p1_sigs.txt
        grep -E "warn: ($REFCOUNT_PATTERN)" "$pass2_warns" 2>/dev/null | \
            sed 's/^[0-9]\+://' | sort -u > /tmp/_p2_sigs.txt

        comm -13 /tmp/_p1_sigs.txt /tmp/_p2_sigs.txt > "$p2_only" 2>/dev/null || true
        local new_count
        new_count=$(wc -l < "$p2_only" 2>/dev/null || echo 0)

        if [[ "$new_count" -gt 0 ]]; then
            echo "=== Cross-function New Warnings (in Pass 2 only) ==="
            cat "$p2_only"
            echo ""
        fi
    else
        new_count=0
    fi

    # 提取正样例: 路径上 get/put 平衡的 refcount 操作
    local pass1_balanced="$RESULT_DIR/pass1_balanced_refcount.txt"
    local pass2_balanced="$RESULT_DIR/pass2_balanced_refcount.txt"
    {
        echo "# Smatch Pass 1 Balanced Refcount (Positive Samples)"
        echo "# Generated: $(date)"
        echo "#"
        echo ""
        grep -nE "info: balanced refcount" "$pass1_warns" 2>/dev/null || echo "# No balanced refcount found."
    } > "$pass1_balanced"

    {
        echo "# Smatch Pass 2 Balanced Refcount (Positive Samples, with cross-function)"
        echo "# Generated: $(date)"
        echo "#"
        echo ""
        grep -nE "info: balanced refcount" "$pass2_warns" 2>/dev/null || echo "# No balanced refcount found."
    } > "$pass2_balanced"

    local p1_balanced_count
    p1_balanced_count=$(grep -cE "info: balanced refcount" "$pass1_warns" 2>/dev/null || echo 0)
    local p2_balanced_count
    p2_balanced_count=$(grep -cE "info: balanced refcount" "$pass2_warns" 2>/dev/null || echo 0)

    # 生成摘要
    local summary_json="$RESULT_DIR/summary.json"
    cat > "$summary_json" <<JSONEOF
{
  "timestamp": "$TIMESTAMP",
  "kernel": "$KERNEL_DIR",
  "smatch_bin": "$SMATCH_BIN",
  "smatch_enable": "$SMATCH_ENABLE",
  "config_mode": "$CONFIG_MODE",
  "jobs": $JOBS,
  "target": "${TARGET_FILE:-${TARGET_DIR:-all}}",
  "pass1": {
    "total_warnings": $(wc -l < "$pass1_warns" 2>/dev/null || echo 0),
    "refcount_warnings": $p1_count,
	    "uaf_warnings": $p1_uaf,
    "balanced_refcount": $p1_balanced_count,
    "output": "$pass1_refcount"
  },
  "pass2": {
    "total_warnings": $(wc -l < "$pass2_warns" 2>/dev/null || echo 0),
    "refcount_warnings": $p2_count,
	    "uaf_warnings": $p2_uaf,
	    "must_check_warnings": $p2_mc,
    "balanced_refcount": $p2_balanced_count,
    "output": "$pass2_refcount"
  },
  "cross_function": {
    "new_warnings": $new_count,
    "output": "$p2_only"
  },
  "balanced_refcount": {
    "pass1": "$pass1_balanced",
    "pass2": "$pass2_balanced"
  },
  "database": "$RESULT_DIR/smatch_db.sqlite"
}
JSONEOF

    echo ""
    echo "============================================"
    echo "  Results Summary"
    echo "============================================"
    echo "  Pass 1 (intra) refcount    : $p1_count"
	    echo "  Pass 1 (intra) UAF         : $p1_uaf"
    echo "  Pass 1 (intra) balanced    : $p1_balanced_count"
    echo "  Pass 2 (cross-func) refcount: $p2_count"
	    echo "  Pass 2 (cross-func) UAF    : $p2_uaf"
	    echo "  Pass 2 (cross-func) must_ck: $p2_mc"
    echo "  Pass 2 (cross-func) balanced: $p2_balanced_count"
    echo "  New (cross-func only)      : $new_count"
    echo ""
    echo "  Pass 1 warns       : $pass1_warns"
    echo "  Pass 1 balanced    : $pass1_balanced"
    echo "  Pass 2 warns       : $pass2_warns"
    echo "  Pass 2 balanced    : $pass2_balanced"
    echo "  Pass 2 only warns  : $p2_only"
    echo "  Summary            : $summary_json"
    echo "============================================"
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo "============================================"
    echo "  s8: Smatch Cross-Function Refcount Detector"
    echo "  $(date)"
    echo "============================================"
    echo ""

    check_prerequisites

    if [[ "$BUILD_SMATCH" -eq 1 ]]; then
        build_smatch
    fi

    if [[ "$PASS2_ONLY" -ne 1 ]]; then
        configure_kernel
        run_pass1
        build_database
    fi

    if [[ "$PASS1_ONLY" -ne 1 ]]; then
        run_pass2
        collect_and_compare
    fi

    echo ""
    echo "Done."
}

main
