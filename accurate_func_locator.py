#!/usr/bin/env python3
"""
AccurateFuncLocator -- 准确查找 Linux 内核函数实现

分层定位策略:
  1. cscope -L1          查找定义位置（文件 + 起始行号）
  2. 状态机括号匹配器     确定函数结束行（注释/字符串/字符感知）
  3. 严格模式校验         确保提取的代码是真正的函数定义
  4. 多定义消歧           取实现行数最多的那个（最完整的实现）

前序操作:
  在目标内核源码目录执行: make cscope
  或调用: locator.prepare_cscope()
"""

import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 状态机常量
# ---------------------------------------------------------------------------
(S_NORMAL, S_STRING, S_STRING_ESC, S_CHAR, S_CHAR_ESC,
 S_LINE_COMMENT, S_BLOCK_COMMENT, S_BLOCK_COMMENT_END,
 S_PREPROCESSOR, S_PREPROCESSOR_CONT) = range(10)


class AccurateFuncLocator:
    """精确查找 C 函数实现的定位器"""

    def __init__(self, linux_source_dir: str, cscope_db_path: Optional[str] = None,
                 cscope_bin: str = "cscope"):
        self.linux_source_dir = os.path.abspath(linux_source_dir)
        self.cscope_db_path = cscope_db_path or os.path.join(self.linux_source_dir, "cscope.out")
        self.cscope_bin = cscope_bin
        if not os.path.exists(self.cscope_db_path):
            print(f"Warning: cscope database not found at {self.cscope_db_path}")

    def prepare_cscope(self) -> bool:
        """
        在内核源码目录中生成 cscope 索引数据库。
        执行: make cscope (需要内核 Makefile 支持)
        返回 True 表示成功。
        """
        if os.path.exists(self.cscope_db_path):
            print(f"cscope database already exists at {self.cscope_db_path}")
            return True

        print(f"Generating cscope index for {self.linux_source_dir} ...")
        try:
            result = subprocess.run(
                ["make", "cscope"],
                cwd=self.linux_source_dir,
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode == 0 and os.path.exists(self.cscope_db_path):
                print("cscope index generated successfully.")
                return True
            else:
                print(f"make cscope failed (rc={result.returncode})")
                if result.stderr:
                    print(f"  stderr: {result.stderr[:500]}")
                return False
        except subprocess.TimeoutExpired:
            print("make cscope timed out (10 min)")
            return False
        except Exception as e:
            print(f"prepare_cscope error: {e}")
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_function_source(self, func_name: str, prefer_c_file: bool = True) -> dict:
        """
        查找函数实现并返回源代码。
        返回:
          {
            "source_code": str,        # 完整的函数源代码
            "file_path": str,           # 文件绝对路径
            "start_line": int,          # 函数定义的起始行 (1-based)
            "end_line": int,            # 函数定义的结束行 (1-based)
            "confidence": "high"|"medium"|"low",
            "is_definition": bool,      # True = 定义, False = 可能是声明
          }
          如果找不到，返回 {"source_code": "", ...} with is_definition=False
        """
        all_defs = self.find_all_definitions(func_name)
        if not all_defs:
            return self._empty_result()

        # 消歧：取实现行数最多的那个（最完整的实现）
        # 1. 先为每个候选提取源码并校验
        verified = []    # (result_dict, line_count, file_path)
        unverified = []  # (result_dict, line_count, file_path)
        for d in all_defs:
            source, ok = self._extract_and_verify(d["file_path"], d["start_line"], func_name)
            end_line = d.get("end_line", d["start_line"])
            line_count = end_line - d["start_line"] + 1
            result = {
                "source_code": source,
                "file_path": d["file_path"],
                "start_line": d["start_line"],
                "end_line": end_line,
                "confidence": d.get("confidence", "medium"),
                "is_definition": ok,
            }
            if ok:
                verified.append((result, line_count))
            else:
                unverified.append((result, line_count))

        # 2. 优先从校验通过的候选中选行数最多的
        if verified:
            verified.sort(key=lambda x: x[1], reverse=True)
            return verified[0][0]

        # 3. 都没有通过校验时，从非 tools/ 中选行数最多的
        if unverified:
            non_tools = [(r, lc) for r, lc in unverified if "/tools/" not in r["file_path"]]
            candidates = non_tools if non_tools else unverified
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return self._empty_result()

    def find_all_definitions(self, func_name: str) -> List[dict]:
        """
        返回函数的所有定义位置。
        每个元素:
          {
            "file_path": str,
            "start_line": int,
            "end_line": int,
            "confidence": "high"|"medium"|"low",
            "definition_text": str,   # cscope 返回的定义行文本
          }
        """
        entries = self._cscope_l1(func_name)
        if not entries:
            entries = self._ctags_fallback(func_name)

        results = []
        for entry in entries:
            file_path = entry["file_path"]
            start_line = entry["start_line"]
            end_line, confidence = self._find_function_end(file_path, start_line, func_name)
            results.append({
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "confidence": confidence,
                "definition_text": entry.get("definition_text", ""),
            })

        return results

    # ------------------------------------------------------------------
    # 第一层：cscope 查找定义
    # ------------------------------------------------------------------

    def _cscope_l1(self, func_name: str) -> List[dict]:
        """
        cscope -L1: 查找函数定义。
        输出格式: filename func_name line_number definition_text
        例: net/core/dst.c dst_release 165 void dst_release(struct dst_entry *dst)
        """
        if not os.path.exists(self.cscope_db_path):
            return []

        try:
            result = subprocess.run(
                [self.cscope_bin, "-d", "-L1", func_name],
                cwd=self.linux_source_dir,
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return []

            entries = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(None, 3)  # 最多分 4 段
                if len(parts) < 3:
                    continue
                filename, found_name, line_str = parts[0], parts[1], parts[2]
                definition_text = parts[3] if len(parts) > 3 else ""

                if not line_str.isdigit():
                    continue
                start_line = int(line_str)

                file_path = os.path.join(self.linux_source_dir, filename)
                if not os.path.exists(file_path):
                    continue

                entries.append({
                    "file_path": file_path,
                    "start_line": start_line,
                    "found_name": found_name,
                    "definition_text": definition_text,
                })

            return entries
        except Exception as e:
            print(f"cscope -L1 error for {func_name}: {e}")
            return []

    # ------------------------------------------------------------------
    # 第二层：状态机括号匹配
    # ------------------------------------------------------------------

    def _find_function_end(self, file_path: str, start_line: int,
                           func_name: str) -> Tuple[int, str]:
        """
        用注释/字符串感知的状态机括号匹配确定函数结束行。
        返回 (end_line: int, confidence: str)
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return start_line + 50, "low"

        total = len(lines)
        if start_line > total:
            return min(start_line + 10, total), "low"

        # 从 cscope 报告的行附近寻找包含 func_name 的行和函数的 {
        sig_line = self._find_signature_line(lines, start_line - 1, func_name)
        if sig_line is None:
            return self._estimate_end(lines, start_line - 1), "low"

        # 找到函数体的 {
        brace_line = self._find_opening_brace(lines, sig_line)
        if brace_line is None:
            return self._estimate_end(lines, sig_line), "low"

        # 状态机括号匹配
        depth = 0
        in_body = False

        for i in range(brace_line, min(brace_line + 5000, total)):
            line = lines[i]
            braces = self._count_braces_stateful(line)

            for b in braces:
                if b == "{":
                    depth += 1
                    in_body = True
                elif b == "}":
                    depth -= 1

                if in_body and depth == 0:
                    return i + 1, "high"  # 1-based

        # 未在 5000 行内找到平衡
        if in_body and depth > 0:
            return min(brace_line + 5000, total), "low"
        return self._estimate_end(lines, brace_line), "low"

    def _find_signature_line(self, lines: List[str], start_idx: int,
                             func_name: str) -> Optional[int]:
        """在 start_idx 附近找到包含 func_name 的行。"""
        search_start = max(0, start_idx - 5)
        search_end = min(len(lines), start_idx + 50)

        for i in range(start_idx, search_end):
            if func_name in lines[i]:
                return i
        for i in range(search_start, start_idx):
            if func_name in lines[i]:
                return i
        return None

    def _find_opening_brace(self, lines: List[str], sig_line: int) -> Optional[int]:
        """从签名行向后找第一个 {（函数体开始）。"""
        total = len(lines)
        for i in range(sig_line, min(sig_line + 30, total)):
            stripped = self._strip_non_code(lines[i])
            if "{" in stripped:
                return i
        return None

    def _count_braces_stateful(self, line: str) -> List[str]:
        """
        使用状态机过滤注释/字符串/字符后返回该行的有效括号序列。
        返回仅包含 '{' 和 '}' 的列表。
        """
        braces = []
        state = S_NORMAL
        n = len(line)

        i = 0
        while i < n:
            ch = line[i]
            nxt = line[i + 1] if i + 1 < n else ""

            if state == S_NORMAL:
                if ch == '"':
                    state = S_STRING
                elif ch == "'":
                    state = S_CHAR
                elif ch == "/" and nxt == "/":
                    break  # 行剩余部分是注释
                elif ch == "/" and nxt == "*":
                    state = S_BLOCK_COMMENT
                    i += 1
                elif ch == "#":
                    # 预处理指令行 — 检查行尾续行符
                    state = S_PREPROCESSOR
                elif ch == "{":
                    braces.append("{")
                elif ch == "}":
                    braces.append("}")

            elif state == S_STRING:
                if ch == "\\" and nxt:
                    state = S_STRING_ESC
                    i += 1
                elif ch == '"':
                    state = S_NORMAL

            elif state == S_STRING_ESC:
                state = S_STRING

            elif state == S_CHAR:
                if ch == "\\" and nxt:
                    state = S_CHAR_ESC
                    i += 1
                elif ch == "'":
                    state = S_NORMAL

            elif state == S_CHAR_ESC:
                state = S_CHAR

            elif state == S_BLOCK_COMMENT:
                if ch == "*" and nxt == "/":
                    state = S_NORMAL
                    i += 1

            # 预处理指令中: 不计数括号
            elif state == S_PREPROCESSOR:
                if ch == "\\" and nxt:
                    state = S_PREPROCESSOR_CONT
                elif ch == "\n":
                    state = S_NORMAL

            # 预处理续行
            elif state == S_PREPROCESSOR_CONT:
                state = S_PREPROCESSOR

            i += 1

        return braces

    def _strip_non_code(self, line: str) -> str:
        """去掉注释/字符串后返回该行的可执行代码部分，仅用于查找 {。"""
        result = []
        state = S_NORMAL
        n = len(line)

        i = 0
        while i < n:
            ch = line[i]
            nxt = line[i + 1] if i + 1 < n else ""

            if state == S_NORMAL:
                if ch == '"':
                    state = S_STRING
                elif ch == "'":
                    state = S_CHAR
                elif ch == "/" and nxt == "/":
                    break
                elif ch == "/" and nxt == "*":
                    state = S_BLOCK_COMMENT
                    i += 1
                else:
                    result.append(ch)

            elif state == S_STRING:
                if ch == "\\" and nxt:
                    state = S_STRING_ESC
                    i += 1
                elif ch == '"':
                    state = S_NORMAL

            elif state == S_STRING_ESC:
                state = S_STRING

            elif state == S_CHAR:
                if ch == "\\" and nxt:
                    state = S_CHAR_ESC
                    i += 1
                elif ch == "'":
                    state = S_NORMAL

            elif state == S_CHAR_ESC:
                state = S_CHAR

            elif state == S_BLOCK_COMMENT:
                if ch == "*" and nxt == "/":
                    state = S_NORMAL
                    i += 1

            i += 1

        return "".join(result)

    def _estimate_end(self, lines: List[str], start_idx: int) -> int:
        """快速估算：当状态机无法准确确定时的回退策略。"""
        total = len(lines)
        return min(start_idx + 51, total)  # 1-based

    # ------------------------------------------------------------------
    # 第三层：严格校验
    # ------------------------------------------------------------------

    def _extract_and_verify(self, file_path: str, start_line: int,
                            func_name: str) -> Tuple[str, bool]:
        """
        提取源代码并严格校验。
        返回 (source_code, is_verified)。
        """
        end_line, confidence = self._find_function_end(file_path, start_line, func_name)
        source = self._read_source(file_path, start_line, end_line)

        if not source:
            return "", False

        # 校验 1：函数名必须出现在代码中
        if func_name not in source:
            return source, False

        # 校验 2：必须有能匹配的函数定义/声明模式
        if not self._has_definition_pattern(source, func_name):
            return source, False

        return source, True

    def _has_definition_pattern(self, source: str, func_name: str) -> bool:
        """
        检查源代码中是否存在函数定义模式（非仅 callee 调用）。
        模式: func_name 必须出现在类似函数签名/定义的上下文中。
        """
        # 去掉注释和字符串后再检查
        clean_lines = []
        for line in source.split("\n"):
            clean_lines.append(self._strip_non_code(line))
        clean = "\n".join(clean_lines)

        # 函数定义模式:
        #   返回值类型 func_name(参数...) {
        #   或者宏包装的版本
        patterns = [
            # 标准定义: type func_name(...)  {
            r'\b' + re.escape(func_name) + r'\s*\([^{;]*\)\s*\{',
            # func_name( 后跨行到 { 的情况
            r'\b' + re.escape(func_name) + r'\s*\([^{;]*\)\s*$',
        ]

        for pattern in patterns:
            if re.search(pattern, clean, re.MULTILINE):
                return True

        # 宽松模式：func_name 后跟 ( 且该行不以 ; 结束（通常不是调用）
        for line in clean.split("\n"):
            if re.search(r'\b' + re.escape(func_name) + r'\s*\(', line):
                if not line.rstrip().endswith(";"):
                    return True

        return False

    def _read_source(self, file_path: str, start_line: int, end_line: int) -> str:
        """读取文件的指定行范围。"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()

            read_start = max(0, start_line - 1)
            read_end = min(len(all_lines), end_line)

            if read_start >= len(all_lines):
                return ""

            return "".join(all_lines[read_start:read_end])
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # 第四层：多定义消歧
    # ------------------------------------------------------------------

    def _resolve_definitions(self, definitions: List[dict]) -> List[dict]:
        """
        对多个定义进行排序消歧:
        1. 非 tools/ 目录优先于 tools/
        2. .c 文件优先于 .h 文件
        3. include/linux/ 优先于 arch/
        """
        def _score(d):
            s = 0
            fp = d.get("file_path", "")
            # 排除 tools/ 测试目录
            if "/tools/" in fp:
                s -= 100
            # .c 优先
            if fp.endswith(".c"):
                s += 10
            # 核心头文件优先于架构特定头文件
            if "/include/linux/" in fp:
                s += 5
            if "/arch/" in fp:
                s -= 5
            # 高置信度优先
            conf = d.get("confidence", "low")
            if conf == "high":
                s += 3
            elif conf == "medium":
                s += 1
            return s

        return sorted(definitions, key=_score, reverse=True)

    # ------------------------------------------------------------------
    # ctags 回退
    # ------------------------------------------------------------------

    def _ctags_fallback(self, func_name: str) -> List[dict]:
        """当 cscope 不可用时的 ctags 回退方案。"""
        try:
            result = subprocess.run(
                ["ctags", "-R", "--languages=c", "--c-kinds=+f", "--fields=+ne",
                 "-o", "-"],
                cwd=self.linux_source_dir,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                return []

            entries = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                if parts[0] != func_name:
                    continue

                file_path = parts[1]
                if not os.path.isabs(file_path):
                    file_path = os.path.join(self.linux_source_dir, file_path)

                start_line = None
                for field in parts[3:]:
                    if field.startswith("line:"):
                        try:
                            start_line = int(field[5:])
                        except ValueError:
                            pass
                        break

                if start_line and os.path.exists(file_path):
                    entries.append({
                        "file_path": file_path,
                        "start_line": start_line,
                        "found_name": func_name,
                        "definition_text": "",
                    })
            return entries
        except Exception as e:
            print(f"ctags fallback error for {func_name}: {e}")
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_result(self) -> dict:
        return {
            "source_code": "",
            "file_path": "",
            "start_line": 0,
            "end_line": 0,
            "confidence": "low",
            "is_definition": False,
        }

    def cscope_db_exists(self) -> bool:
        return os.path.exists(self.cscope_db_path)


# -----------------------------------------------------------------------
# 便捷函数 —— 与原有 s1_caller_function_agent 接口兼容
# -----------------------------------------------------------------------

def find_func_source_code_with_locator(target_func_name: str,
                                       locator: AccurateFuncLocator) -> str:
    """
    使用 AccurateFuncLocator 查找函数源代码。
    与现有 find_func_source_code() 返回格式兼容（返回纯字符串）。
    """
    result = locator.find_function_source(target_func_name)
    if result["is_definition"]:
        return result["source_code"]
    if result["source_code"]:
        return result["source_code"]
    return ""


if __name__ == "__main__":
    # 测试
    import sys

    linux_dir = os.environ.get("REFCOUNT_KERNEL_DIR", ".")
    locator = AccurateFuncLocator(linux_dir)

    test_funcs = [
        "refcount_inc",
        "refcount_dec_and_test",
        "kref_get",
        "kref_put",
        "dst_release",
        "ip_rt_put",
        "__refcount_add",
        "kzalloc",
    ]

    if len(sys.argv) > 1:
        test_funcs = sys.argv[1:]

    for fname in test_funcs:
        print(f"\n{'='*70}")
        print(f"Function: {fname}()")
        print(f"{'='*70}")

        result = locator.find_function_source(fname)
        print(f"  File:      {result['file_path']}")
        print(f"  Lines:     {result['start_line']}-{result['end_line']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Is def:    {result['is_definition']}")
        print(f"  Source length: {len(result['source_code'])} chars")
        if result["source_code"]:
            preview = result["source_code"][:500]
            print(f"  Preview:\n{preview}")
