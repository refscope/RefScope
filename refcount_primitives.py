#!/usr/bin/env python3
"""
Level 0 — Refcount Primitive Functions 硬编码类型链表

所有 refcount primitive 函数的精确 type_chain 和 access_path。
这些是手工验证的绝对基准，作为整个传播推导的 Level 0 起点。

类型定义 (来自内核头文件):
  struct refcount_struct { atomic_t refs; };
  typedef struct refcount_struct refcount_t;
  struct kref { refcount_t refcount; };

对于 refcount_t 类型的参数:
  - type_chain: "refcount_struct--atomic_t"
  - 在参数上的完整 access 是 r->refs (smatch key: $->refs.counter)

对于 atomic_t 类型的参数:
  - type_chain: "atomic_t"
  - 在参数上的完整 access 是 r->counter (smatch key: $->counter)

对于 kref 类型的参数:
  - type_chain: "kref--refcount_struct--atomic_t"
  - 在参数上的完整 access 是 kref.refcount.refs (smatch key: $->refcount.refs.counter)
"""

from typing import Dict, Any, Optional

# ─────────────────────────────────────────────────────────────────────
# 内部结构
# ─────────────────────────────────────────────────────────────────────
# 每个 primitive 条目:
# {
#     "direction": "get" | "put" | "set",
#     "location": "parameter" | "return",
#     "param_index": 1-based parameter index (0 = return value),
#     "type_chain":  "--" 分隔的类型链 如 "refcount_struct--atomic_t",
#     "access_path": "." 分隔的字段访问路径 如 "refs",
#     "notes":       可选的说明文字
# }


# ─────────────────────────────────────────────────────────────────────
# atomic_t 族 — 直接操作 atomic_t
# ─────────────────────────────────────────────────────────────────────

_ATOMIC_GETS = {
    "atomic_inc":                  (1,),
    "atomic_long_inc":             (1,),
    "atomic64_inc":                (1,),
    "atomic_inc_return":           (1,),
    "atomic_long_inc_return":      (1,),
    "atomic64_inc_return":         (1,),
    "atomic64_inc_not_zero":       (1,),
}

_ATOMIC_GETS_PARAM2 = {
    # functions where param 1 = value, param 2 = ptr
    "atomic_add_return":           (2,),
    "atomic_long_add_return":      (2,),
    "atomic64_add_return":         (2,),
}

_ATOMIC_PUTS = {
    "atomic_dec":                  (1,),
    "atomic_long_dec":             (1,),
    "atomic64_dec":                (1,),
    "atomic_dec_return":           (1,),
    "atomic_long_dec_return":      (1,),
    "atomic64_dec_return":         (1,),
    "atomic_dec_and_test":         (1,),
    "atomic_long_dec_and_test":    (1,),
    "atomic64_dec_and_test":       (1,),
    "atomic_dec_if_positive":      (1,),
    "atomic64_dec_if_positive":    (1,),
    "_atomic_dec_and_lock":        (1,),
}

_ATOMIC_PUTS_PARAM2 = {
    "atomic_sub":                  (2,),
    "atomic_long_sub":             (2,),
    "atomic64_sub":                (2,),
    "atomic_sub_return":           (2,),
    "atomic_long_sub_return":      (2,),
    "atomic64_sub_return":         (2,),
    "atomic_sub_and_test":         (2,),
    "atomic_long_sub_and_test":    (2,),
    "atomic64_sub_and_test":       (2,),
}


# ─────────────────────────────────────────────────────────────────────
# refcount_t 族 — 操作 refcount_struct { atomic_t refs; }
# ─────────────────────────────────────────────────────────────────────

_REFCOUNT_GETS = {
    "refcount_inc":                (1,),
    "refcount_inc_not_zero":       (1,),
}

_REFCOUNT_GETS_PARAM2 = {
    "refcount_add":                (2,),
    "refcount_add_not_zero":       (2,),
    "refcount_inc_not_zero_acquire": (2,),
    "refcount_add_not_zero_acquire": (2,),
}

_REFCOUNT_PUTS = {
    "refcount_dec":                (1,),
    "refcount_dec_and_test":       (1,),
    "__refcount_dec_and_test":     (1,),
    "refcount_dec_if_one":         (1,),
    "refcount_dec_not_one":        (1,),
}

_REFCOUNT_PUTS_PARAM2 = {
    "refcount_sub_and_test":       (2,),
    "__refcount_sub_and_test":     (2,),
}

_REFCOUNT_SETS = {
    # refcount_set sets refcount to a specific value (set operation, param 1 = ptr, param 2 = value)
    "refcount_set":                (1,),
    "refcount_set_release":        (1,),
}


# ─────────────────────────────────────────────────────────────────────
# kref 族 — 操作 kref { refcount_t refcount; }
# ─────────────────────────────────────────────────────────────────────

_KREF_SETS = {
    "kref_init":                   (1,),
}


# ─────────────────────────────────────────────────────────────────────
# rcuref 族 — 操作 rcuref_t (RCU-protected refcount)
# ─────────────────────────────────────────────────────────────────────

_RCUREF_GETS = {
    "rcuref_get":                  (1,),
}

_RCUREF_PUTS = {
    "rcuref_put":                  (1,),
}


# ─────────────────────────────────────────────────────────────────────
# 组装
# ─────────────────────────────────────────────────────────────────────

def _build_primitive_table() -> Dict[str, Dict[str, Any]]:
    """构建完整的 primitive 表。"""
    table: Dict[str, Dict[str, Any]] = {}

    def _add(func_names, direction, type_chain, access_path, param_index):
        for name in func_names:
            table[name] = {
                "direction": direction,
                "location": "parameter",
                "param_index": param_index,
                "type_chain": type_chain,
                "access_path": access_path,
            }

    # atomic_t primitives
    for func_set, param_idx in [
        (_ATOMIC_GETS, 1),
        (_ATOMIC_GETS_PARAM2, 2),
    ]:
        _add(func_set, "get", "atomic_t", "counter", param_idx)

    for func_set, param_idx in [
        (_ATOMIC_PUTS, 1),
        (_ATOMIC_PUTS_PARAM2, 2),
    ]:
        _add(func_set, "put", "atomic_t", "counter", param_idx)

    # refcount_t primitives
    _add(_REFCOUNT_GETS, "get", "refcount_struct--atomic_t", "refs", 1)
    _add(_REFCOUNT_GETS_PARAM2, "get", "refcount_struct--atomic_t", "refs", 2)
    _add(_REFCOUNT_PUTS, "put", "refcount_struct--atomic_t", "refs", 1)
    _add(_REFCOUNT_PUTS_PARAM2, "put", "refcount_struct--atomic_t", "refs", 2)
    _add(_REFCOUNT_SETS, "set", "refcount_struct--atomic_t", "refs", 1)

    # kref primitives
    _add(_KREF_SETS, "set", "kref--refcount_struct--atomic_t", "refcount.refs", 1)

    # rcuref primitives
    _add(_RCUREF_GETS, "get", "rcuref--atomic_t", "refcnt", 1)
    _add(_RCUREF_PUTS, "put", "rcuref--atomic_t", "refcnt", 1)

    return table


# 全局单例
REFCOUNT_PRIMITIVES: Dict[str, Dict[str, Any]] = _build_primitive_table()


# ─────────────────────────────────────────────────────────────────────
# 查询接口
# ─────────────────────────────────────────────────────────────────────

def is_primitive(func_name: str) -> bool:
    """判断一个函数是否是 refcount primitive。"""
    return func_name in REFCOUNT_PRIMITIVES


def get_primitive_info(func_name: str) -> Optional[Dict[str, Any]]:
    """获取 primitive 的完整类型信息。"""
    return REFCOUNT_PRIMITIVES.get(func_name)


def get_primitive_type_chain(func_name: str) -> Optional[str]:
    """获取 primitive 的 type_chain 字符串。"""
    info = REFCOUNT_PRIMITIVES.get(func_name)
    return info["type_chain"] if info else None


def get_primitive_access_path(func_name: str) -> Optional[str]:
    """获取 primitive 的 access_path。"""
    info = REFCOUNT_PRIMITIVES.get(func_name)
    return info["access_path"] if info else None


def get_all_primitive_names() -> list:
    """返回所有 primitive 函数名列表。"""
    return sorted(REFCOUNT_PRIMITIVES.keys())


# ─────────────────────────────────────────────────────────────────────
# 自检
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Total primitives: {len(REFCOUNT_PRIMITIVES)}")
    print()
    by_dir = {}
    for name, info in sorted(REFCOUNT_PRIMITIVES.items()):
        d = info["direction"]
        by_dir.setdefault(d, []).append(name)
    for d in ["get", "put", "set"]:
        names = by_dir.get(d, [])
        print(f"  {d} ({len(names)}):")
        for n in sorted(names)[:10]:
            print(f"    {n:45s}  tc={REFCOUNT_PRIMITIVES[n]['type_chain']}")
        if len(names) > 10:
            print(f"    ... and {len(names)-10} more")
        print()
