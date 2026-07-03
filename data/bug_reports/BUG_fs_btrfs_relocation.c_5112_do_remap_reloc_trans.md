# REAL BUG: fs/btrfs/relocation.c:5112 do_remap_reloc_trans()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

**No ownership transfer or deferred cleanup is documented** for either extra reference; `dest_bg` is local and `src_bg` is an input parameter. The contracts define the get semantics and do **not** indicate any internal release in those functions.

## Full Response

```
| Line | Return Type | GET1 (lookup dest_bg) | GET2 (adjust dest_bg) | GET3 (mark src_bg) | PUT dest_bg | PUT src_bg | Balanced? | Notes |
|------|-------------|----------------------|------------------------|---------------------|-------------|------------|-----------|-------|
|   22 | error       | NO (before call)     | NO                     | NO                  | N/A         | N/A        | ✅        | early return |
|   27 | error       | NO                   | NO                     | NO                  | N/A         | N/A        | ✅        | |
|   35 | goto next   | NO (before call)     | NO                     | NO                  | N/A         | N/A        | ✅        | dest_bg still NULL at next |
|   39 | error       | NO                   | NO                     | NO                  | N/A         | N/A        | ✅        | |
|   61 | error       | NO                   | NO                     | NO                  | N/A         | N/A        | ✅        | |
|   95 | goto fail   | YES                  | NO                     | NO                  | YES         | N/A        | ✅        | fail: dest_bg put once |
|  102 | goto fail   | YES                  | NO                     | NO                  | YES         | N/A        | ✅        | |
|  108 | goto fail   | YES                  | NO                     | NO                  | YES         | N/A        | ✅        | |
|  114 | goto fail   | YES                  | NO                     | NO                  | YES         | N/A        | ✅        | |
|  149 | return ret  | YES                  | YES                    | YES (if cond)       | YES (one)   | NO         | ❌        | dest_bg leak (2 refs, 1 put); src_bg leak if mark called |
|  152 | return 1    | YES                  | YES                    | YES (if cond)       | YES (one)   | NO         | ❌        | |
|  156 | return 0    | YES                  | YES                    | YES (if cond)       | YES (one)   | NO         | ❌        | |

- `btrfs_lookup_block_group()` acquires one reference on `dest_bg` (GET1).
- `adjust_block_group_remap_bytes()` calls `btrfs_get_block_group()` and per contract adds an extra reference on `dest_bg` (GET2).
- `btrfs_mark_bg_fully_remapped()` calls `btrfs_get_block_group()` and per contract adds a reference on `src_bg` (GET3).
- After the `next:` label, `dest_bg` is released **once**, ignoring the extra reference from `adjust_block_group_remap_bytes()`.
- All returns after `next:` that are reachable when `adjust_block_group_remap_bytes()` was called leak that extra reference on `dest_bg`.
- If the condition for `btrfs_mark_bg_fully_remapped()` is true, those same returns also leak the new reference on `src_bg` (no put at all).

**No ownership transfer or deferred cleanup is documented** for either extra reference; `dest_bg` is local and `src_bg` is an input parameter. The contracts define the get semantics and do **not** indicate any internal release in those functions.

VERDICT: REAL_BUG
CO
```
