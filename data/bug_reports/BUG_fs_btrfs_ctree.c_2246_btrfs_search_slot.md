# REAL BUG: fs/btrfs/ctree.c:2246 btrfs_search_slot()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| `done` (any other path that stored b) | L2233 | return | (stored) | ✅ error: `btrfs_release_path` | ✅ | |

## Full Response

```
| Path Description | Line(s) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|-----------------|---------|-------------|-----------|-----------|-----------|-------|
| `root == NULL` | L2018 | error return `-EINVAL` | NO | N/A | ✅ | before any get |
| `need_commit_sem` trylock fail | L2063 | error return `-EAGAIN` | NO | N/A | ✅ | before any get |
| `btrfs_search_slot_get_root` returns IS_ERR | L2072-L2074 | `goto done` (error) | NO (get failed) | N/A | ✅ | IS_ERR guard |
| write‑lock adjust, root NOT stored, `goto again` | L2098-L2105 | restart (`goto again`) | YES (root `b` from get) | NO (`btrfs_release_path` only touches path) | ❌ LEAK | root `b` leaked |
| `btrfs_cow_block` error, `goto done` | L2116-L2118 | `goto done` (error) | YES (old root `b`) | NO (b not stored in path, `done` will NOT free it) | ❌ LEAK | old root leaked |
| `level == 0` after `cow_done`, `goto done` | L2144-L2152 | `goto done` | YES (b stored) | ✅ (path release on error, caller later) | ✅ | |
| `search_for_key_slot` error, `goto done` | L2155-L2157 | `goto done` (error) | YES (b stored) | ✅ | ✅ | |
| `setup_nodes_for_search` error, `goto done` | L2171-L2173 | `goto done` (error) | YES (b stored) | ✅ | ✅ | |
| `setup_nodes_for_search` returns `-EAGAIN`, `goto again` | L2167-L2169 | restart (`goto again`) | YES (b stored in path) | NO (path not released; overwritten by new get_root) | ❌ LEAK | old root leaked |
| slot‑zero adjustment, `btrfs_release_path` then `goto again` | L2183-L2187 | restart (`goto again`) | YES (b stored) | YES (release_path) | ✅ | |
| `level == lowest_level`, `goto done` | L2193-L2196 | `goto done` | YES (b stored) | ✅ | ✅ | |
| `read_block_for_search` returns `-EAGAIN` (no nowait), `goto again` | L2199-L2202 | restart (`goto again`) | YES (old parent b stored) | NO (path not released) | ❌ LEAK | old root leaked |
| `read_block_for_search` error (not EAGAIN), `goto done` | L2204-L2206 | `goto done` (error) | YES (old parent b stored) | ✅ | ✅ | |
| try‑lock fails (nowait), `free_extent_buffer(b)` and `goto done` | L2219-L2222 | `goto done` (error) | YES (new b) | YES (explicit `free_extent_buffer`) | ✅ | |
| loop exits normally (`ret = 1`) | L2232 | `goto done` (success) | YES (nodes stored in path) | ✅ (caller later) | ✅ | |
| `done` (any other path that stored b) | L2233 | return | (stored) | ✅ error: `btrfs_release_path` | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Multiple restart (`goto again`) paths and the `btrfs_cow_block` error path fail to release the reference acquired by `btrfs_search_slot_get_root`, leading to refcount leaks.
```
