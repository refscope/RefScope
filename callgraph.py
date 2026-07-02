#!/usr/bin/env python3
"""
callgraph.py - 生成函数调用关系
"""
import subprocess
import sys
import os

def prepare_cscope(linux_dir):
    """准备cscope数据库"""
    os.chdir(linux_dir)
    subprocess.run(["make", "cscope"], check=False)

def get_callers(func_name, linux_dir):
    """获取函数被谁调用（调用者）"""
    try:
        result = subprocess.run(
            ["cscope", "-d", "-L3", func_name],
            capture_output=True,
            text=True,
            cwd=linux_dir
        )
        if result.returncode == 0:
            callers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 4:
                        callers.append({
                            'caller': parts[1],
                            'file': parts[0],
                            'line': parts[2],
                            'context': ' '.join(parts[3:])
                        })
            return callers
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
    return []


def print_callers(func_name, depth=1, linux_dir="", indent=""):
    """递归打印调用关系（谁调用了这个函数）"""
    if depth <= 0:
        return
    
    callers = get_callers(func_name, linux_dir)
    if not callers:
        print(f"{indent}{func_name} 未被其他函数调用")
        return
    
    for caller in callers:
        print(f"{indent}{caller['caller']} 在 {caller['file']}:{caller['line']} 调用了 {func_name}")
        if depth > 1:
            # 递归查找调用者的调用者
            print_callers(caller['caller'], depth-1, linux_dir, indent + "  ")




if __name__ == "__main__":
    # Linux内核目录作为参数传递给main函数
    linux_directory = os.environ.get("REFCOUNT_KERNEL_DIR", ".")
    function_name = "vxlan_xmit_one"
    depth = 2  # 设置递归深度

    if not os.path.exists(os.path.join(linux_directory, "cscope.out")):
        prepare_cscope(linux_directory)
    
    print(f"查找函数 {function_name} 被哪些函数调用：")
    print_callers(function_name, depth, linux_directory, "")
