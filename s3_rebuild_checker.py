#!/usr/bin/env python3
"""
Kernel Checker Scanner - 简化版
使用 clang scan-build 对内核源代码进行静态分析
"""

import json
import os
import sys
import subprocess
import argparse
import shutil
from datetime import datetime
from pathlib import Path


PAIR_CANDIDATE_FILENAME = "function_pair_candidates.json"


def load_function_pairs_from_candidates(function_result_dir, min_score=0.5, match_types=None):
    """
    从 function_pair_candidates.json 加载函数对。

    Args:
        function_result_dir: FunctionResult 目录路径
        min_score: 最低分数阈值 (默认 0.5)
        match_types: 允许的 match_type 列表。None 表示全部允许。
                     可选值: "strict", "lcs", "best_effort"
                     常用组合:
                       ["strict", "lcs"]  — 仅高质量匹配，忽略 best_effort
                       ["best_effort"]    — 仅兜底匹配
                       None               — 全部包含

    Returns:
        [(get_functions, put_functions), ...]
    """
    candidate_path = os.path.join(function_result_dir, PAIR_CANDIDATE_FILENAME)
    with open(candidate_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    if match_types is not None:
        match_types = set(match_types)

    function_pairs = []
    for candidate in candidates:
        if candidate.get("score", 0) < min_score:
            continue
        if match_types is not None:
            mtype = candidate.get("evidence", {}).get("match_type", "strict")
            if mtype not in match_types:
                continue
        get_functions = sorted(set(candidate.get("get_functions", [])))
        put_functions = sorted(set(candidate.get("put_functions", [])))
        if get_functions and put_functions:
            function_pairs.append((get_functions, put_functions))
    return function_pairs


def copy_sample_checker(sample_file, target_file):
    """
    复制样本检查器文件到目标位置

    Args:
        sample_file: 样本检查器文件路径
        target_file: 目标检查器文件路径
    """
    with open(sample_file, "r") as src:
        content = src.read()
    with open(target_file, "w") as dst:
        dst.write(content)



def write_file(checker_file, function_pair_list):
    """
    将函数列表写入指定文件

    Args:
        checker_file: 输出文件路径
        get_function_list: 获取函数列表
        put_function_list: 放置函数列表
    """

    cur = 0
    function_checker_declearation = []
    put_function_content = []
    put_function_checker_define = []
    get_function_content = []
    get_function_checker_define = []
    for function_pair in function_pair_list:
        function_checker_declearation.append(f"  CHECK_FN(checkFree{cur})\n")
        function_checker_declearation.append(f"  CHECK_FN(checkBasicAlloc{cur})\n")
        get_function_checker_define.append(f"void MallocChecker::checkBasicAlloc{cur}(ProgramStateRef State,\n                                    const CallEvent &Call,\n                                    CheckerContext &C) const {{\n  State = MallocMemAux(C, Call, Call.getArgExpr(0), UndefinedVal(), State,\n                       AllocationFamily(AF_Malloc));\n  State = ProcessZeroAllocCheck(C, Call, 0, State);\n  C.addTransition(State);\n}}\n")
        put_function_checker_define.append(f"\nvoid MallocChecker::checkFree{cur}(ProgramStateRef State, const CallEvent &Call,\n                              CheckerContext &C) const {{\n  bool IsKnownToBeAllocatedMemory = false;\n  if (suppressDeallocationsInSuspiciousContexts(Call, C))\n    return;\n  State = FreeMemAux(C, Call, State, 0, false, IsKnownToBeAllocatedMemory,\n                     AllocationFamily(AF_Malloc));\n  C.addTransition(State);\n}}\n")
        for put_function in function_pair[1]:
            put_function_content.append(f"      {{{{CDM::CLibrary, {{\"{put_function}\"}}, 1}}, &MallocChecker::checkFree{cur}}},\n")
        for get_function in function_pair[0]:
            get_function_content.append(f"      {{{{CDM::CLibrary, {{\"{get_function}\"}}, 1}}, &MallocChecker::checkBasicAlloc{cur}}},\n")
        cur += 1

    with open(checker_file, "r") as f:
        lines = f.readlines()
    with open(checker_file, "w") as f:
        function_checker_declearation_pos = 422 -1
        put_function_content_pos = 468 - 1 + len(function_checker_declearation)
        get_function_content_pos = 509 - 1 + len(put_function_content) + len(function_checker_declearation)
        put_function_checker_define_pos = 1334 - 1 + len(function_checker_declearation) + len(put_function_content) + len(get_function_content)
        get_function_checker_define_pos = 1344 - 1 + len(function_checker_declearation) + len(put_function_content) + len(get_function_content) + len(put_function_checker_define)
        lines = lines[:function_checker_declearation_pos] + function_checker_declearation + lines[function_checker_declearation_pos:]
        lines = lines[:put_function_content_pos] + put_function_content + lines[put_function_content_pos:]
        lines = lines[:get_function_content_pos] + get_function_content + lines[get_function_content_pos:]
        lines = lines[:put_function_checker_define_pos] + put_function_checker_define + lines[put_function_checker_define_pos:]
        lines = lines[:get_function_checker_define_pos] + get_function_checker_define + lines[get_function_checker_define_pos:]
        f.writelines(lines)



def build_checker(clang_dir):
    """
    构建自定义的 Clang 静态分析检查器

    Args:
        clang_dir: Clang 源代码目录路径
    """
    clang_dir = Path(clang_dir).resolve()
    build_dir = clang_dir / "build"
    shutil.rmtree(build_dir, ignore_errors=True)
    build_dir.mkdir(exist_ok=True)

    print("构建自定义检查器...")
    clang_src_dir = clang_dir / "clang-20.1.8.src"
    result = subprocess.run(
        ['cmake -G "Unix Makefiles"'
         f' -S {clang_src_dir}'
         f' -B {build_dir}'
         ' -DCMAKE_BUILD_TYPE=Release'
         ' -DLLVM_DIR="$(llvm-config-20 --cmakedir)"'
         f' -DCMAKE_MODULE_PATH="{clang_src_dir}/cmake/modules"'
         ' -DLLVM_INCLUDE_TESTS=OFF'
         ' -DCLANG_INCLUDE_TESTS=OFF'
         ' -DCLANG_ENABLE_EXTRA_CLANG_TOOLS=ON'],
        cwd=build_dir,
        shell=True,
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ CMake 配置失败")
        return False

    result = subprocess.run(
        ["make -j64"],
        cwd=build_dir,
        shell=True,
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ 检查器构建失败")
        return False

    result = subprocess.run(
        ["make install"],
        cwd=build_dir,
        shell=True,
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ 检查器安装失败")
        return False



def run_scan(target_dir, output_dir=None, jobs=64, skip_config=False):
    """
    运行内核静态分析扫描

    Args:
        target_dir: 内核源代码目录路径
        output_dir: 扫描结果输出目录 (默认: DataShare/Bug/YYMMDD)
        jobs: make 并行任务数 (默认: 64)
        skip_config: 跳过内核配置步骤 (默认: False)

    Returns:
        bool: 扫描是否成功完成
    """
    target_dir = Path(target_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if not target_dir.exists():
        print(f"错误: 目标目录不存在: {target_dir}")
        return False
    if not target_dir.is_dir():
        print(f"错误: 目标路径不是目录: {target_dir}")
        return False
    output_dir.mkdir(parents=True, exist_ok=True)

    print("步骤 0: (make clean)...")
    subprocess.run(["make", "clean"], cwd=target_dir, capture_output=False)

    if not skip_config:
        print("步骤 1: 配置内核 (make allyesconfig)...")
        result = subprocess.run(["make", "allyesconfig"], cwd=target_dir, capture_output=False)
        if result.returncode != 0:
            print("✗ 内核配置失败")
            return False
        print("✓ 内核配置完成\n")
    else:
        print("跳过内核配置步骤\n")

    print("步骤 2: 运行 scan-build 分析...")

    disabled_checkers = [
        "core.BitwiseShift", "core.CallAndMessage", "core.DivideZero",
        "core.NonNullParamChecker", "core.NullDereference", "core.StackAddressEscape",
        "core.UndefinedBinaryOperatorResult", "core.VLASize",
        "core.uninitialized.ArraySubscript", "core.uninitialized.Assign",
        "core.uninitialized.Branch", "core.uninitialized.CapturedBlockVariable",
        "core.uninitialized.NewArraySize", "core.uninitialized.UndefReturn",
        "cplusplus.ArrayDelete", "cplusplus.InnerPointer", "cplusplus.Move",
        "cplusplus.NewDelete", "cplusplus.NewDeleteLeaks", "cplusplus.PlacementNew",
        "cplusplus.PureVirtualCall", "cplusplus.StringChecker", "deadcode.DeadStores",
        "fuchsia.HandleChecker", "nullability.NullPassedToNonnull",
        "nullability.NullReturnedFromNonnull", "nullability.NullableDereferenced",
        "nullability.NullablePassedToNonnull", "nullability.NullableReturnedFromNonnull",
        "optin.core.EnumCastOutOfRange", "optin.cplusplus.UninitializedObject",
        "optin.cplusplus.VirtualCall", "optin.mpi.MPI-Checker",
        "optin.osx.OSObjectCStyleCast",
        "optin.osx.cocoa.localizability.EmptyLocalizationContextChecker",
        "optin.osx.cocoa.localizability.NonLocalizedStringChecker",
        "optin.performance.GCDAntipattern", "optin.performance.Padding",
        "optin.portability.UnixAPI", "optin.taint.GenericTaint",
        "optin.taint.TaintedAlloc", "optin.taint.TaintedDiv",
        "osx.API", "osx.MIG", "osx.NumberObjectConversion", "osx.OSObjectRetainCount",
        "osx.ObjCProperty", "osx.SecKeychainAPI", "osx.cocoa.AtSync",
        "osx.cocoa.AutoreleaseWrite", "osx.cocoa.ClassRelease", "osx.cocoa.Dealloc",
        "osx.cocoa.IncompatibleMethodTypes", "osx.cocoa.Loops",
        "osx.cocoa.MissingSuperCall", "osx.cocoa.NSAutoreleasePool",
        "osx.cocoa.NSError", "osx.cocoa.NilArg", "osx.cocoa.NonNilReturnValue",
        "osx.cocoa.ObjCGenerics", "osx.cocoa.RetainCount",
        "osx.cocoa.RunLoopAutoreleaseLeak", "osx.cocoa.SelfInit",
        "osx.cocoa.SuperDealloc", "osx.cocoa.UnusedIvars",
        "osx.cocoa.VariadicMethodTypes", "osx.coreFoundation.CFError",
        "osx.coreFoundation.CFNumber", "osx.coreFoundation.CFRetainRelease",
        "osx.coreFoundation.containers.OutOfBounds",
        "osx.coreFoundation.containers.PointerSizedValues",
        "security.FloatLoopCounter", "security.MmapWriteExec", "security.PointerSub",
        "security.PutenvStackArray", "security.SetgidSetuidOrder",
        "security.cert.env.InvalidPtr",
        "security.insecureAPI.DeprecatedOrUnsafeBufferHandling",
        "security.insecureAPI.UncheckedReturn", "security.insecureAPI.bcmp",
        "security.insecureAPI.bcopy", "security.insecureAPI.bzero",
        "security.insecureAPI.decodeValueOfObjCType", "security.insecureAPI.getpw",
        "security.insecureAPI.gets", "security.insecureAPI.mkstemp",
        "security.insecureAPI.mktemp", "security.insecureAPI.rand",
        "security.insecureAPI.strcpy", "security.insecureAPI.vfork",
        "unix.API", "unix.BlockInCriticalSection", "unix.Chroot", "unix.Errno",
        "unix.MallocSizeof", "unix.MismatchedDeallocator", "unix.StdCLibraryFunctions",
        "unix.Stream", "unix.Vfork", "unix.cstring.BadSizeArg",
        "unix.cstring.NotNullTerminated", "unix.cstring.NullArg",
        "valist.CopyToSelf", "valist.Uninitialized", "valist.Unterminated",
        "webkit.NoUncountedMemberChecker", "webkit.RefCntblBaseVirtualDtor",
        "webkit.UncountedLambdaCapturesChecker",
    ]

    cmd = ["/usr/local/bin/scan-build", "--use-cc=/usr/local/bin/clang-20"]
    for checker in disabled_checkers:
        cmd.extend(["-disable-checker", checker])
    cmd.extend(["-enable-checker", "unix.Malloc"])
    cmd.extend(["-o", str(output_dir), "--status-bugs", "make", f"-j{jobs}"])

    print(f"运行命令: {' '.join(cmd)}\n")
    result = subprocess.run([' '.join(cmd)], shell=True, cwd=target_dir)

    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✓ 扫描成功完成!")
    else:
        print("⚠ 扫描完成但有警告或错误")
    print("=" * 60)
    print(f"结果保存至: {output_dir}")

    return result.returncode == 0


if __name__ == "__main__":
    clang_dir = os.environ.get("REFCOUNT_CLANG_DIR", "")
    if not clang_dir:
        print("ERROR: REFCOUNT_CLANG_DIR environment variable is required.")
        print("  export REFCOUNT_CLANG_DIR=/path/to/clang-checker")
        sys.exit(1)

    checker_sample_file = os.path.join(clang_dir, "MallocChecker_sample.cpp")
    copied_checker_file = os.path.join(clang_dir, "clang-20.1.8.src/lib/StaticAnalyzer/Checkers/MallocChecker.cpp")
    function_result_dir = os.environ.get(
        "REFCOUNT_FUNCTION_RESULT_DIR",
        os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "FunctionResult", "default")
    )

    # --- 选择 match_type 组合 ---
    # Mode 1: strict + lcs（忽略 best_effort）
    match_types = ["strict", "lcs"]
    # Mode 2: 仅 best_effort
    # match_types = ["best_effort"]
    # Mode 3: 全部
    # match_types = None

    copy_sample_checker(checker_sample_file, copied_checker_file)

    pairs = load_function_pairs_from_candidates(function_result_dir, min_score=0.5, match_types=match_types)
    print(f"Loaded {len(pairs)} pair candidates (match_types={match_types})")
    for i, (gets, puts) in enumerate(pairs):
        print(f"  pair {i}: gets={gets[:3]}...  puts={puts[:3]}...")

    write_file(copied_checker_file, pairs)
    build_checker(clang_dir)

    target_dir = os.environ.get("REFCOUNT_KERNEL_DIR", "")
    output_dir = os.environ.get("REFCOUNT_BUG_DIR", os.path.join(os.environ.get("REFCOUNT_DATA_DIR", "./data"), "Bug", "default"))
    jobs = 64
    skip_config = False

    run_scan(target_dir, output_dir, jobs, skip_config)
