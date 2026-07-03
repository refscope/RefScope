# REAL BUG: fs/btrfs/zoned.c:2709 btrfs_zone_finish_endio()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| 2706 (fall through to out) | goto out → return 0 | YES (lookup succeeded) | YES in `do_zone_finish` + YES again at out | ❌ | `do_zone_finish` consumes the reference, then `btrfs_put_block_group` at out double-puts → EXCESS PUT |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 2686 | return 0   | NO (before get) | N/A  | ✅ | `btrfs_is_zoned` false, no ref taken |
| 2693 | return -ENOENT | NO (lookup returned NULL, conditional get gave no ref) | N/A | ✅ | WARN_ON_ONCE triggers, no ref held |
| 2703 | goto out → return 0 | YES (lookup succeeded) | YES (btrfs_put_block_group at out) | ✅ | One get, one put |
| 2706 (fall through to out) | goto out → return 0 | YES (lookup succeeded) | YES in `do_zone_finish` + YES again at out | ❌ | `do_zone_finish` consumes the reference, then `btrfs_put_block_group` at out double-puts → EXCESS PUT |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`btrfs_lookup_block_group` acquires a ref; `do_zone_finish` performs an unconditional put (contract says it calls `btrfs_put_block_group`), but the code unconditionally falls through to `out` which does a second put, causing a refcount underflow.
```
