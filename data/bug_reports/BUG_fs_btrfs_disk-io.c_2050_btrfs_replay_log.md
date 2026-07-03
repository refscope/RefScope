# REAL BUG: fs/btrfs/disk-io.c:2050 btrfs_replay_log()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L2049| success (return 0)      | YES       | YES (caller put at L2036) + callee put on success | ❌ **DOUBLE PUT** | same double-put as above.

## Full Response

```
```
| Line | Return Type            | GET Done? | PUT Done?       | Balanced? | Notes |
|------|------------------------|-----------|-----------------|-----------|-------|
| L2014| error, before alloc    | NO        | N/A             | ✅        | return -EIO, no get. |
| L2020| error, alloc returned NULL | NO (alloc failed) | N/A         | ✅        | btrfs_alloc_root NULL ⇒ no ref held. |
| L2031| error, read_tree_block failed | YES       | YES (btrfs_put_root at L2030) | ✅ | alloc succeeded, clean up. |
| L2040| error, btrfs_recover_log_trees failed | YES | YES (btrfs_put_root at L2036) | ✅ (assuming callee does NOT put on error; comment says “freed on success” only) | |
| L2046| error, sb_rdonly commit failed (after recover success) | YES | YES (caller put at L2036) but callee already put on success | ❌ **DOUBLE PUT** | Comment: “returns with log_tree_root freed on success” → btrfs_recover_log_trees calls btrfs_put_root. Caller’s put is extra → refcount goes negative. |
| L2049| success (return 0)      | YES       | YES (caller put at L2036) + callee put on success | ❌ **DOUBLE PUT** | same double-put as above.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On success of `btrfs_recover_log_trees()` the comment states the root is freed, but the caller unconditionally calls `btrfs_put_root()` after the function, leading to a double-put (refcount underflow) on the success path (lines L2046 and L2049). This matches the “inconsistent refcounting” warning at line 2050 (function exit).```
```
