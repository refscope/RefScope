#!/usr/bin/env python3
"""
将 FunctionResult 中的 get/put/set 函数配置到 smatch 的引用计数检测器中。

从指定目录读取所有 JSON 文件，
提取 final.functionality_list 中的 get/put 操作，生成 smatch_refcount_info.c 的
func_table[] 条目，并插入到目标文件中。

Usage:
    python s6_configure_smatch_refcount.py
    python s6_configure_smatch_refcount.py --dry-run          # 仅预览，不写入
    python s6_configure_smatch_refcount.py --output /tmp/out.c # 输出到指定文件
"""

import json
import os
import sys
import argparse
from collections import defaultdict


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

FUNCTION_RESULT_DIR = os.environ.get(
    "REFCOUNT_FUNCTION_RESULT_DIR",
    os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "FunctionResult", "default")
)
SMATCH_REFCOUNT_INFO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smatch", "smatch_refcount_info.c")

# smatch 操作类型常量 (定义于 smatch_dbtypes.h:148-150)
REFCOUNT_INIT = "REFCOUNT_INIT"
REFCOUNT_INC = "REFCOUNT_INC"
REFCOUNT_DEC = "REFCOUNT_DEC"


def load_function_data(data_dir):
    """
    从数据目录加载所有函数的 get/put 操作信息。

    Returns:
        list of dict: 每个元素包含 function_name, operation_type, location,
                      param_index, member_path, type_chain
    """
    entries = []
    stats = defaultdict(int)

    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(data_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            continue

        func_name = data.get("function_name", "")
        if not func_name:
            continue

        # 从 final 或顶层获取 functionality_list
        final = data.get("final", {})
        if isinstance(final, list):
            # final 是列表的，跳过（data 本身可能无有效信息）
            fl = data.get("functionality_list", [])
        elif isinstance(final, dict):
            if final.get("status") != "ok":
                continue
            fl = final.get("functionality_list", [])
            conditionality = final.get("conditionality", "unconditional")
            must_check = final.get("must_check", False)
        else:
            fl = []
            conditionality = "unconditional"
            must_check = False

        if not fl:
            stats['empty_fl'] += 1
            continue

        stats['with_operations'] += 1

        for item in fl:
            if len(item) < 5:
                continue
            op_type = item[0]   # "get" or "put" or "set"
            location = item[1]  # "parameter" or "return"
            param_idx = item[2] # "1", "2", ... or "0" (return)
            member_path = item[3]  # e.g. "l.count.count.refs"
            type_chain = item[4]   # e.g. "aa_label--kref--refcount_t--atomic_t"

            stats[f'op_{op_type}_{location}'] += 1
            stats[f'conditionality_{conditionality}'] += 1

            entry = {
                "function_name": func_name,
                "operation_type": op_type,
                "location": location,
                "param_index": param_idx,
                "member_path": member_path,
                "type_chain": type_chain,
                "conditionality": conditionality,
                "must_check": must_check,
            }
            entries.append(entry)

    stats['total_functions'] = len(set(e['function_name'] for e in entries))
    stats['total_entries'] = len(entries)

    return entries, stats


def map_to_smatch_param(location, param_index):
    """
    将数据中的 location/index 映射为 smatch 的参数索引。

    - parameter + "1" → 0 (第一个参数)
    - parameter + "2" → 1 (第二个参数)
    - return + "0" → -1 (返回值)
    """
    if location == "return":
        return -1
    # parameter
    try:
        return int(param_index) - 1
    except (ValueError, TypeError):
        return -1


def clean_member_path(member_path):
    """
    清理 member_access_path，去除变量名前缀。

    数据路径的第一段通常是代码中的变量名（参数名或返回变量名），
    smatch 使用 $-> 直接访问对象成员，因此需要去掉变量名前缀。
    如果路径只有一段且无法确定是否为变量名，保守保留。

    Examples:
        "l.count.count.refs" → "count.count.refs"
        "orig.proxy.label.count.count" → "proxy.label.count.count"
        "ct.ct_general.use.refs" → "ct_general.use.refs"
        "refcount.refs" → "refcount.refs" (无变量前缀)
        "r.refs" → "refs"
        "refcount" → "refcount" (单段保留)
    """
    path = member_path.strip()

    segments = path.split('.')
    # 只有一段时无法判断是否是变量名，保守保留
    if len(segments) <= 1:
        return path

    # 两段以上：第一段是变量名，去掉
    return '.'.join(segments[1:])


def resolve_counter_path(member_path, type_chain):
    """
    根据 type_chain 解析出 smatch 所需的完整 counter 路径。

    smatch 中的引用计数检测始终追踪 atomic_t 内部的 .counter 字段。
    数据中的 member_access_path 末尾可能没有包含 .counter，
    需要根据 type_chain 追加。

    规则：
    - type_chain 以 atomic_t 结尾：路径末尾字段即为 atomic_t，追加 .counter
    - type_chain 以 refcount_t 结尾：路径末尾字段即为 refcount_t，追加 .refs.counter
    - 其他类型：保守兜底，检查路径是否已包含 .counter，否则追加 .counter

    Returns:
        str: 完整的 smatch key 路径（不含 $-> 前缀）
    """
    cleaned = clean_member_path(member_path)

    if not type_chain:
        return cleaned

    chain_parts = [t.strip() for t in type_chain.split('--')]
    last_type = chain_parts[-1] if chain_parts else ''

    if last_type == 'atomic_t':
        if not cleaned.endswith('.counter'):
            return cleaned + '.counter'
    elif last_type == 'refcount_t':
        if not cleaned.endswith('.refs.counter'):
            if cleaned.endswith('.refs'):
                return cleaned + '.counter'
            else:
                return cleaned + '.refs.counter'
    else:
        # 兜底：确保以 .counter 结尾
        if not cleaned.endswith('.counter'):
            return cleaned + '.counter'

    return cleaned


def map_op_type(op_type):
    """将 get/put/set 映射为 smatch 常量。"""
    if op_type == "get":
        return REFCOUNT_INC
    elif op_type == "set":
        return REFCOUNT_INIT
    else:
        return REFCOUNT_DEC


def is_unconditional_get(entry):
    """
    根据 function 的条件性信息判断 get/set 操作是否无条件执行。

    conditionality 的规范值 (来自 s1 prompt template_judge.prompt):
      - "unconditional"          : 操作始终执行，永不失败
      - "conditional_on_path"    : 操作仅在特定代码路径上执行
      - "conditional_on_nonnull" : 操作仅在对象指针非 NULL 时执行
      - "conditional_on_nonzero" : 操作仅在引用计数非零时成功

    非规范值处理:
      - 包含 "conditional" 的变体 → 视为条件性 (conservative)
      - 空字符串 / "none" / "not_applicable" / "unknown" / None → 视为无条件 (保守)
    """
    op_type = entry.get("operation_type", "")
    conditionality = entry.get("conditionality", "unconditional")

    # set 始终无条件——初始化引用计数为 1
    if op_type == "set":
        return True

    # get 和 put：根据 conditionality 决定
    # conditional_on_path/nonnull/nonzero → 仅在成功路径上执行
    # unconditional → 在所有路径上都执行
    if not conditionality or conditionality in (None, "", "none", "not_applicable",
                                                  "unknown", "N/A", "n/a", "null", "false"):
        return True  # 保守默认：无条件

    if conditionality == "unconditional":
        return True

    # 所有条件性变体
    if "conditional" in str(conditionality).lower():
        return False

    return True  # 兜底


def generate_func_table_entry(entry):
    """
    生成单条 func_table 条目字符串。

    unconditional_get 规则:
      - set (REFCOUNT_INIT): 始终 true (初始化总是执行)
      - get (REFCOUNT_INC):  根据 function 的 conditionality 决定
      - put (REFCOUNT_DEC):  根据 function 的 conditionality 决定 (与 get 对称)
    """
    func_name = entry["function_name"]
    smatch_op = map_op_type(entry["operation_type"])
    smatch_param = map_to_smatch_param(entry["location"], entry["param_index"])
    counter_path = resolve_counter_path(entry["member_path"], entry["type_chain"])
    smatch_key = f"$->{counter_path}"

    unconditional = "true" if is_unconditional_get(entry) else "false"
    must_check = entry.get("must_check", False)
    must_check_str = ", true" if must_check else ""

    return f'\t{{ "{func_name}", {smatch_op}, {smatch_param}, "{smatch_key}", NULL, NULL, NULL, {unconditional}{must_check_str} }},'


def generate_all_entries(entries, sort_by_func=True):
    """
    为所有条目生成 func_table 代码行。

    Args:
        entries: load_function_data 返回的条目列表
        sort_by_func: 是否按函数名排序（便于阅读）

    Returns:
        list of str: 每行一个条目
    """
    if sort_by_func:
        entries = sorted(entries, key=lambda e: (e["function_name"], e["operation_type"]))

    # 去重（相同函数+相同操作+相同路径的条目只保留一个）
    seen = set()
    unique_entries = []
    for e in entries:
        key = (e["function_name"], e["operation_type"], e["location"],
               e["param_index"], e["member_path"])
        if key not in seen:
            seen.add(key)
            unique_entries.append(e)

    lines = []
    for e in unique_entries:
        line = generate_func_table_entry(e)
        lines.append(line)

    return lines


def insert_into_smatch_refcount_info(source_file, new_entries_lines, dry_run=False):
    """
    将新条目插入到 smatch_refcount_info.c 的 func_table[] 数组中。

    在现有 func_table[] 数组的最后一个条目之后、闭合大括号之前插入新条目。
    """
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
        original_lines = content.split('\n')

    # 找到 func_table[] 的定义范围
    in_func_table = False
    table_start = None
    table_end = None

    for i, line in enumerate(original_lines):
        if 'static struct ref_func_info func_table[]' in line:
            in_func_table = True
            table_start = i
            continue
        if in_func_table and line.strip() == '};':
            table_end = i
            break

    if table_start is None or table_end is None:
        print("Error: Could not find func_table[] in source file")
        return False

    # 在 table_end 之前插入新条目
    indent = "\t"
    insert_lines = [f"{indent}/* === Auto-generated entries from s6_configure_smatch_refcount.py === */"]
    insert_lines.extend(new_entries_lines)
    insert_lines.append("")  # 空行分隔

    new_lines = (original_lines[:table_end] +
                 insert_lines +
                 original_lines[table_end:])

    new_content = '\n'.join(new_lines)

    if dry_run:
        print(f"\n[DRY RUN] Would insert {len(new_entries_lines)} entries into {source_file}")
        print(f"  Insert position: after line {table_end} (before the closing }}; of func_table[])")
        print(f"\n  First 10 entries to insert:")
        for line in insert_lines[:12]:
            print(f"    {line}")
        return True

    # 确保目标目录存在
    os.makedirs(os.path.dirname(source_file) or ".", exist_ok=True)

    # 备份原文件
    backup = source_file + ".bak"
    if not os.path.exists(backup):
        with open(backup, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Backup created: {backup}")

    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Inserted {len(new_entries_lines)} entries into {source_file}")
    print(f"  Insert position: after line {table_end}")
    print(f"  Total lines: {len(original_lines)} → {len(new_lines)}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Configure get/put functions into smatch refcount detector"
    )
    parser.add_argument(
        "--data-dir",
        default=FUNCTION_RESULT_DIR,
        help=f"Directory containing function JSON files (default: {FUNCTION_RESULT_DIR})",
    )
    parser.add_argument(
        "--output",
        default=SMATCH_REFCOUNT_INFO,
        help=f"Target smatch_refcount_info.c file (default: {SMATCH_REFCOUNT_INFO})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to file",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=0,
        help="Preview first N entries and exit without modifying files",
    )
    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Show statistics about the data",
    )
    args = parser.parse_args()

    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory not found: {args.data_dir}")
        sys.exit(1)

    if not args.dry_run and not args.preview and not os.path.exists(args.output):
        print(f"Error: Target file not found: {args.output}")
        sys.exit(1)

    print(f"Loading function data from: {args.data_dir}")
    entries, stats = load_function_data(args.data_dir)

    if args.show_stats or True:
        print(f"\n--- Statistics ---")
        for k, v in sorted(stats.items()):
            print(f"  {k}: {v}")

    if not entries:
        print("\nNo entries found. Exiting.")
        return

    print(f"\nGenerating smatch func_table entries...")
    all_lines = generate_all_entries(entries, sort_by_func=True)
    print(f"  Total unique entries: {len(all_lines)}")

    if args.preview > 0:
        print(f"\n--- Preview (first {args.preview}) ---")
        for line in all_lines[:args.preview]:
            print(line)
        return

    if args.dry_run:
        print(f"\n--- Dry Run ---")
        print(f"Would insert {len(all_lines)} entries into {args.output}")
        print(f"\nFirst 10 entries:")
        for line in all_lines[:10]:
            print(line)
        if len(all_lines) > 10:
            print(f"  ... and {len(all_lines) - 10} more")
        return

    # 确认操作
    print(f"\nAbout to insert {len(all_lines)} entries into:")
    print(f"  {args.output}")
    response = input("Continue? [y/N]: ").strip().lower()
    if response not in ('y', 'yes'):
        print("Cancelled.")
        return

    success = insert_into_smatch_refcount_info(args.output, all_lines)
    if success:
        print("\nDone! You can now rebuild smatch to use the updated detector.")
        print(f"  cd {os.path.dirname(SMATCH_REFCOUNT_INFO)} && make")


if __name__ == "__main__":
    main()
