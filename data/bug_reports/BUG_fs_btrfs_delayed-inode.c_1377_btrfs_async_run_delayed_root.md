# REAL BUG: fs/btrfs/delayed-inode.c:1377 btrfs_async_run_delayed_root()

**Confidence**: MEDIUM | **Counter**: `$->refs.refs.counter`

## Reasoning

| L1367‑1369 (success iteration, while condition true → continue) | loop continues | YES | YES + extra PUT | ❌ EXCESS PUT (same double‑put in each such iteration) | same as above, repeated across iterations |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1334 (`goto out`) | exit (via out) | NO | NO | ✅ | allocation failure before any get |
| L1339 (`break`) | exit loop → out | NO | NO | ✅ | items check before any get |
| L1344 (`break`) | exit loop → out | NO | NO | ✅ | get returned NULL, no ref held |
| L1354 (`continue`) | loop iteration end | YES (L1341 non‑NULL) | YES (L1351‑1352 explicit put) | ✅ (this iteration) | IS_ERR trans path – one get, one put |
| L1367‑1369 (success iteration, then while condition false → exit) | loop exit → out | YES (L1341 non‑NULL) | YES (L1367‑1368 explicit put) + **extra PUT inside __btrfs_commit_inode_delayed_items** (according to smatch) | ❌ EXCESS PUT | explicit put after __btrfs_commit_inode_delayed_items which already releases the ref → double put |
| L1367‑1369 (success iteration, while condition true → continue) | loop continues | YES | YES + extra PUT | ❌ EXCESS PUT (same double‑put in each such iteration) | same as above, repeated across iterations |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`btrfs_async_run_delayed_root()` calls `__btrfs_commit_inode_delayed_items()` which according to smatch already consumes the delayed_node reference, then the caller unconditionally calls `btrfs_release_prepared_delayed_node()` on the same node, leading to an excess (double) put on the node’s refcount.
```
