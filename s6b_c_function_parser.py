#!/usr/bin/env python3
"""
s6b — 简易 C 函数体解析器

从 C 源码中提取函数体、识别 return 语句、变量声明等，
供 s6b_detect_auto_cleanup_bugs.py 使用。

不依赖完整 C 解析器，基于大括号匹配 + 正则表达式。
"""

import re
from typing import Optional, List, Tuple


def extract_function_body(file_path: str, func_name: str,
                          near_line: int = 1) -> Optional[str]:
    """
    从文件中提取指定函数的函数体。

    策略: 从 near_line 向前搜索函数定义行（func_name 出现在行首附近），
    然后从 { 开始追踪大括号配对直到函数结束。
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except (IOError, OSError):
        return None

    # 从 near_line 向前搜索 func_name(
    func_pattern = re.compile(rf'\b{re.escape(func_name)}\s*\(')
    func_def_line = None

    for i in range(near_line - 1, max(0, near_line - 200), -1):
        line = lines[i]
        # 跳过注释
        stripped = line.strip()
        if stripped.startswith('/*') or stripped.startswith('*') or \
           stripped.startswith('//') or stripped.startswith('#'):
            continue
        # 跳过显然不是函数定义的行 (如 func_name(...) 出现在中间)
        if func_pattern.search(line):
            # 验证: 后面要有 {
            if i + 1 < len(lines) and '{' in lines[i + 1]:
                func_def_line = i
                break
            if '{' in line:
                func_def_line = i
                break

    if func_def_line is None:
        # fallback: 向前搜索任何包含 func_name( 的行
        for i in range(near_line - 1, max(0, near_line - 200), -1):
            if func_pattern.search(lines[i]):
                func_def_line = i
                break

    if func_def_line is None:
        return None

    # 从 func_def_line 开始找 {
    brace_start = None
    for i in range(func_def_line, len(lines)):
        if '{' in lines[i]:
            brace_start = i
            break

    if brace_start is None:
        return None

    # 大括号配对追踪
    depth = 0
    brace_end = None
    for i in range(brace_start, len(lines)):
        for ch in lines[i]:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break
        if brace_end is not None:
            break

    if brace_end is None:
        return None

    return ''.join(lines[brace_start:brace_end + 1])


def find_return_statements(func_body: str) -> List[Tuple[str, int]]:
    """
    在函数体中定位所有 return 语句。

    Returns:
        list of (return_expression, relative_line_number)
    """
    lines = func_body.split('\n')
    results = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配 return 语句 (非 return_ptr 宏)
        m = re.match(r'return\s+(.+?)\s*;\s*$', stripped)
        if m:
            expr = m.group(1)
            results.append((expr, i + 1))
        # 匹配裸 return;
        elif re.match(r'return\s*;\s*$', stripped):
            results.append(('', i + 1))
    return results


def find_var_declarations(func_body: str,
                           patterns: List[str]) -> List[Tuple[str, str, int]]:
    """
    在函数体中查找匹配指定模式的变量声明。

    Args:
        func_body: 函数体文本
        patterns: 正则模式列表

    Returns:
        list of (var_name, matched_pattern, line_number)
    """
    results = []
    for pattern in patterns:
        for m in re.finditer(pattern, func_body, re.MULTILINE):
            # 尝试提取变量名 (第二个捕获组通常是变量名)
            groups = m.groups()
            if len(groups) >= 2:
                var_name = groups[1]
            elif len(groups) >= 1:
                var_name = groups[0]
            else:
                var_name = m.group(0)

            # 计算行号
            line_no = func_body[:m.start()].count('\n') + 1
            results.append((var_name.strip(), m.group(0), line_no))
    return results


def function_contains_call(func_body: str, func_name: str,
                            arg_name: str) -> List[int]:
    """
    检查函数体中是否调用了 func_name(arg_name) — 仅匹配直接传参，不匹配成员访问。

    func_name(var)      → 匹配
    func_name(&var)     → 匹配
    func_name(var->x)   → 不匹配 (不同指针)
    func_name(var.x)    → 不匹配 (不同指针)

    Returns:
        匹配到的行号列表
    """
    # 要求 ) 紧跟在 var_name 后面 (允许空格)
    pattern = rf'{re.escape(func_name)}\s*\(\s*(?:&\s*)?{re.escape(arg_name)}\s*\)'
    results = []
    for m in re.finditer(pattern, func_body):
        line_no = func_body[:m.start()].count('\n') + 1
        results.append(line_no)
    return results


def find_no_free_ptr_calls(func_body: str, var_name: str) -> bool:
    """检查函数体中是否有 no_free_ptr(var_name) 或 return_ptr(var_name) 调用。"""
    pattern = rf'(?:no_free_ptr|return_ptr)\s*\(\s*{re.escape(var_name)}\s*\)'
    return bool(re.search(pattern, func_body))


def extract_function_name_from_line(line: str) -> Optional[str]:
    """
    从 C 代码行中提取函数名。

    例如: 'static int foo_bar(' → 'foo_bar'
    """
    # 移除关键字
    for kw in ['static', 'inline', '__always_inline', 'extern',
                'const', 'volatile', 'struct', 'void', 'int', 'long',
                'char', 'bool', 'unsigned', 'signed', 'size_t', 'ssize_t']:
        line = re.sub(rf'\b{kw}\b', '', line)

    # 匹配函数名: identifier + ( + args + )
    m = re.search(r'(\w+)\s*\(', line)
    return m.group(1) if m else None
