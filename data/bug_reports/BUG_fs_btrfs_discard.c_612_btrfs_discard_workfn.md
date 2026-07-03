# REAL BUG: fs/btrfs/discard.c:612 btrfs_discard_workfn()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L612 (path F) | implicit fall‑out when cursor < end | YES | YES (btrfs_put_block_group at L612) | ✅ | No other put on this path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L528 | return (NULL block_group) | NO (peek returned NULL) | N/A | ✅ | Safe – no reference held |
| L540 | early return (!btrfs_run_discard_work) | YES (peek returned non‑NULL) | YES (btrfs_put_block_group inside block) | ✅ | Single put |
| L549 | early return (discard_eligible_time) | YES | YES (btrfs_put_block_group inside block) | ✅ | Single put |
| L612 (path D) | implicit fall‑out after btrfs_finish_discard_pass | YES | YES (btrfs_put_block_group at L612) + possible hidden put inside btrfs_finish_discard_pass | ❌ LIKELY EXCESS | If finish_discard_pass already drops the ref, final put is extra |
| L612 (path E) | implicit fall‑out after else branch (cursor reset) | YES | YES (btrfs_put_block_group at L612) | ✅ | No other put on this path |
| L612 (path F) | implicit fall‑out when cursor < end | YES | YES (btrfs_put_block_group at L612) | ✅ | No other put on this path |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`btrfs_finish_discard_pass` likely consumes the block_group reference (matching its name), so the unconditional `btrfs_put_block_group` at line 612 after that call is an extra put, causing the reported refcount underflow.
```
