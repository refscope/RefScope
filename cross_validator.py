#!/usr/bin/env python3
"""
cross_validator.py — DWARF 枚举 + LLM 兜底

流程:
  Step A: DWARF/pahole 枚举 — 从 caller 参数类型出发，DFS 找到 callee 入口类型
  Step B: 拼接 — caller_partial_chain + callee_type_chain → 完整链
  Step C: 验证 — 逐层确认拼接后的完整链在 DWARF 中存在
  Step D: 输出 — DWARF 成功 → HIGH confidence; 失败 → fallback LLM Extract

输入:
  - caller_func_code, caller_func_name
  - callee_info_list
  - function_result_dir, linux_dir
"""

import json
import os
import re
import sys
from typing import Dict, Any, List, Optional, Tuple

from refcount_primitives import (
    REFCOUNT_PRIMITIVES, is_primitive, get_primitive_info
)
from btf_chain_enumerator import (
    enumerate_chains_from_type, verify_full_chain_btf
)


# ---------------------------------------------------------------------------
# Step 1: 解析 callee type_chain
# ---------------------------------------------------------------------------

def resolve_callee_chain(callee_name: str, function_result_dir: str) -> Optional[Dict]:
    """解析 callee 的 type_chain。优先级: primitive表 → DB。"""
    if is_primitive(callee_name):
        info = get_primitive_info(callee_name)
        tc = _normalize_type_chain(info["type_chain"])
        return {
            "type_chain": tc,
            "access_path": info["access_path"],
            "direction": info["direction"],
            "param_index": info["param_index"],
            "source": "primitives_table",
        }

    db_path = os.path.join(function_result_dir, f"{callee_name}.json")
    if os.path.exists(db_path):
        try:
            with open(db_path) as f:
                entry = json.load(f)
        except (IOError, json.JSONDecodeError):
            return None
        if not entry.get("end_flag"):
            return None
        fl = entry.get("functionality_list", [])
        if not fl or len(fl[0]) < 5:
            return None
        tc = _normalize_type_chain(fl[0][4])
        return {
            "type_chain": tc,
            "access_path": fl[0][3],
            "direction": fl[0][0],
            "param_index": int(fl[0][2]) if isinstance(fl[0][2], (int, str)) and str(fl[0][2]).isdigit() else 1,
            "source": "db",
        }
    return None


def _normalize_type_chain(tc: str) -> str:
    """确保 type_chain 以 atomic_t 结尾。"""
    parts = [p.strip() for p in tc.split("--")]
    if parts[-1] == "atomic_t":
        return tc
    last = parts[-1]
    if last in ("refcount_t", "refcount_struct"):
        return tc + "--atomic_t"
    if last == "rcuref_t":
        return tc + "--atomic_t"
    if last == "kref":
        return tc + "--refcount_struct--atomic_t"
    return tc


# ---------------------------------------------------------------------------
# Step 2: 提取 caller 参数类型
# ---------------------------------------------------------------------------

def _extract_param_types(func_code: str) -> Tuple[Dict[int, str], Dict[int, str], Optional[str]]:
    """从函数签名提取参数类型、参数名、返回值类型。"""
    param_types, param_names, return_type = {}, {}, None
    lines = func_code.split('\n')
    sig_start = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue
        if re.search(r'\w+\s*\(', stripped) and not stripped.startswith(('if ', 'for ', 'while ', 'switch ')):
            sig_start = i
            break
    if sig_start < 0:
        return param_types, param_names, return_type

    sig_text = ''
    depth = 0
    for i in range(sig_start, len(lines)):
        line = lines[i].strip()
        if '//' in line:
            line = line[:line.index('//')]
        sig_text += ' ' + line
        depth += line.count('(') - line.count(')')
        if depth <= 0 and '(' in line:
            break

    sig = sig_text.strip()
    paren_idx = sig.find('(')
    if paren_idx < 0:
        return param_types, param_names, return_type

    before_paren = sig[:paren_idx].strip()
    depth = 0
    close_paren = -1
    for i in range(paren_idx, len(sig)):
        if sig[i] == '(': depth += 1
        elif sig[i] == ')':
            depth -= 1
            if depth == 0:
                close_paren = i
                break
    if close_paren < 0:
        return param_types, param_names, return_type
    params_text = sig[paren_idx + 1:close_paren].strip()

    parts = before_paren.split()
    if len(parts) < 2:
        return param_types, param_names, return_type

    ret_parts = parts[:-1]
    ret_type = ''
    keywords = {'static', 'inline', '__must_check', '__inline', 'extern', '__malloc', '__cold'}
    for p in reversed(ret_parts):
        p_clean = p.strip('*')
        if p_clean not in keywords:
            ret_type = p_clean
            break
    for kw in ['struct ', 'enum ', 'union ', 'const ', 'volatile ']:
        ret_type = ret_type.replace(kw, '')
    if ret_type and ret_type != 'void':
        return_type = ret_type

    if params_text and params_text != 'void':
        for i, param in enumerate(_split_params(params_text)):
            param = param.strip()
            if not param: continue
            parts_list = param.strip().split()
            if len(parts_list) >= 2:
                pname = parts_list[-1].strip('*').strip()
                ptype = ' '.join(parts_list[:-1])
                for kw in ['struct ', 'enum ', 'union ', 'const ', 'volatile ']:
                    ptype = ptype.replace(kw, '')
                param_types[i + 1] = ptype.strip().rstrip('*').strip()
                param_names[i + 1] = pname

    return param_types, param_names, return_type


def _split_params(params_text: str) -> List[str]:
    result, depth, current = [], 0, []
    for c in params_text:
        if c in '([{': depth += 1; current.append(c)
        elif c in ')]}': depth -= 1; current.append(c)
        elif c == ',' and depth == 0: result.append(''.join(current)); current = []
        else: current.append(c)
    if current: result.append(''.join(current))
    return result


# ---------------------------------------------------------------------------
# 主入口: DWARF 枚举 + LLM 兜底
# ---------------------------------------------------------------------------

def extract_type_chain(
    caller_func_name: str,
    caller_func_code: str,
    callee_info_list: List[Dict],
    function_result_dir: str,
) -> Dict[str, Any]:
    """
    DWARF 枚举提取 type_chain。失败时返回标记让上层调 LLM。

    Returns:
        {
            "success": True/False,
            "functionality_list": [...],
            "confidence": "high"|"medium"|"low",
            "source": "dwarf_enumerated"|"dwarf_not_found",
        }
    """
    result = {"success": False, "functionality_list": [], "confidence": "low", "source": "none"}

    callee_chains = {}
    callee_dirs = {}
    for cinfo in callee_info_list:
        name = cinfo.get("callee_function_name", "")
        if name:
            r = resolve_callee_chain(name, function_result_dir)
            if r:
                callee_chains[name] = r
                callee_dirs[name] = r["direction"]
    if not callee_chains:
        result["source"] = "dwarf_not_found(no_callee)"
        return result

    param_types, param_names, return_type = _extract_param_types(caller_func_code)

    # ── 对 EACH callee 枚举: caller param/return → callee entry type → 拼接 callee chain ──
    all_entries = []       # 最终 functionality_list
    need_llm_judge = []    # 一个 callee 操作对应多条链, 需 LLM 判断

    for callee_name, callee_info in callee_chains.items():
        callee_type_chain = callee_info["type_chain"]
        callee_direction = callee_info["direction"]
        callee_access_path = callee_info.get("access_path", "")

        # 对每个 caller 参数枚举
        for pidx, ptype in param_types.items():
            pname = param_names.get(pidx, f"arg{pidx}")
            partials = enumerate_chains_from_type(ptype, callee_type_chain)

            if len(partials) > 1:
                # 一个 callee 操作对应多条链 → 全部交给 LLM
                for pc in partials:
                    tc = _assemble_full_chain(pc, callee_type_chain)
                    ap = _assemble_access_path(pname, pc, callee_access_path)
                    need_llm_judge.append({
                        "callee": callee_name, "direction": callee_direction,
                        "location": "parameter", "param_index": pidx,
                        "access_path": ap, "type_chain": tc,
                    })
            else:
                for pc in partials:
                    tc = _assemble_full_chain(pc, callee_type_chain)
                    ap = _assemble_access_path(pname, pc, callee_access_path)
                    all_entries.append([
                        callee_direction, "parameter", str(pidx), ap, tc
                    ])

        # 对返回值枚举
        if return_type:
            partials = enumerate_chains_from_type(return_type, callee_type_chain)
            if len(partials) > 1:
                for pc in partials:
                    tc = _assemble_full_chain(pc, callee_type_chain)
                    ap = _assemble_access_path("ret", pc, callee_access_path)
                    need_llm_judge.append({
                        "callee": callee_name, "direction": callee_direction,
                        "location": "return", "param_index": 0,
                        "access_path": ap, "type_chain": tc,
                    })
            else:
                for pc in partials:
                    tc = _assemble_full_chain(pc, callee_type_chain)
                    ap = _assemble_access_path("ret", pc, callee_access_path)
                    all_entries.append([
                        callee_direction, "return", "0", ap, tc
                    ])

    # ── 结果 ──
    if all_entries:
        result["success"] = True
        result["functionality_list"] = all_entries
        result["confidence"] = "high" if len(all_entries) <= 2 else "medium"
        result["source"] = "dwarf_enumerated"
        if need_llm_judge:
            result["need_llm_judge"] = need_llm_judge
            result["confidence"] = "medium"
            result["source"] = "dwarf_enumerated(multi_chain_need_llm)"
    elif need_llm_judge:
        # 只有多链候选, 需要 LLM 判断
        result["success"] = True
        result["need_llm_judge"] = need_llm_judge
        result["confidence"] = "low"
        result["source"] = "dwarf_enumerated(need_llm_judge)"
    else:
        result["source"] = "dwarf_not_found"

    return result


def _assemble_full_chain(partial: dict, callee_type_chain: str) -> str:
    """拼接 partial chain + callee chain: caller_param → ... → callee_entry → callee_chain[1:]"""
    callee_parts = callee_type_chain.split("--")
    if len(callee_parts) > 1:
        return partial["partial_type_chain"] + "--" + "--".join(callee_parts[1:])
    return partial["partial_type_chain"]


def _assemble_access_path(param_name: str, partial: dict, callee_access_path: str) -> str:
    """拼接 access_path: caller_param.field1...fieldN.callee_field_chain

    规则: access_path 的段数必须与 type_chain 的 -- 分隔类型数一致。
    callee_access_path 的第一段是 callee 的参数名，需要剥离后再拼接。
    例如: caller param="uuid", fields=["dom"], callee_access_path="dom.ref.refcount"
          → "uuid.dom.ref.refcount" (4段, 与 type_chain 的 4 类型对应)
    """
    fields_joined = ".".join(partial.get("field_path", []))
    ap = param_name + ("." + fields_joined if fields_joined else "")
    if callee_access_path:
        # callee_access_path 的第一段是 callee 参数名, 需剥离
        callee_parts = callee_access_path.split(".", 1)
        suffix = callee_parts[1] if len(callee_parts) > 1 else callee_access_path
        if fields_joined:
            ap += "." + suffix
        else:
            # caller 无字段访问 (直接传参), 用 caller 参数名替换 callee 参数名
            ap += "." + suffix
    return ap
