# REAL BUG: fs/btrfs/block-group.c:2578 read_one_block_group()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L2567 | success (return 0) | YES (creation + load) | NO | ❌ **LEAK** | no put at all; creation ref is intentionally kept for runtime, but the extra ref from load is never released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2467 | error (cache NULL) | NO (creation failed) | N/A | ✅ | no cache allocated |
| L2497 | goto error (before load zone) | YES (creation) | YES (put at L2569) | ✅ | only creation GET; error label releases it |
| L2504 | goto error (load zone failed) | YES (creation + load) | YES (one put at L2569) | ❌ **LEAK** | btrfs_load_block_group_zone_info unconditionally took extra ref; error label puts only creation ref |
| L2516 | goto error (exclude_super_stripes err) | YES (creation + load) | YES (one put at L2569) | ❌ **LEAK** | load already succeeded, extra ref held |
| L2542 | goto error (btrfs_add_new_free_space err) | YES (creation + load) | YES (one put at L2569) | ❌ **LEAK** | same as above |
| L2548 | goto error (btrfs_add_block_group_cache err) | YES (creation + load) | YES (one put at L2569) | ❌ **LEAK** | same |
| L2567 | success (return 0) | YES (creation + load) | NO | ❌ **LEAK** | no put at all; creation ref is intentionally kept for runtime, but the extra ref from load is never released |

**PRE-VERDICT CHECKLIST:**
1. "Held for device lifetime"? Creation ref is for device lifetime, but the extra ref from `btrfs_load_block_group_zone_info` is not covered.
2. "Ownership transferred"? No documented cleanup for the extra ref; no explicit put.
3. Unconditional GET? Yes, `btrfs_load_block_group_zone_info` unconditionally calls `btrfs_get_block_group` per contract.
4. goto out between GET and PUT? Every goto error after L2500 takes an unbalanced path — error label only puts once.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`btrfs_load_block_group_zone_info()` unconditionally increments the block group's refcount (via `btrfs_get_block_group`), but `read_one_block_group()` never releases that extra reference — all paths after the call leak at least one reference.
```
