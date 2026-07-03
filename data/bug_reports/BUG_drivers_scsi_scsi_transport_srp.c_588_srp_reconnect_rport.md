# REAL BUG: drivers/scsi/scsi_transport_srp.c:588 srp_reconnect_rport()

**Confidence**: HIGH | **Counter**: `$->sdev_gendev.kobj.kref.refcount.refs.counter`

## Reasoning

| 10 | state == LOST, res = -ENODEV (state unchanged) | NO | YES | ❌ excess put | Block skipped, unblock in else-if (LOST ≠ BLOCKED) |

## Full Response

```
| Path | Condition | GET (block) | PUT (unblock) | Balanced? | Notes |
|------|-----------|-------------|---------------|-----------|-------|
| 1 | mutex_lock_interruptible fails (L543 → out) | NO | NO | ✅ | No block/unblock |
| 2 | state ≠ FAIL_FAST && ≠ LOST, res == 0 | YES | YES | ✅ | Block/unblock pair |
| 3 | state ≠ FAIL_FAST && ≠ LOST, res ≠ 0, state == RUNNING | YES | NO | ❌ leak | Leak (not excess put) |
| 4 | state ≠ FAIL_FAST && ≠ LOST, res ≠ 0, state ≠ RUNNING && ≠ BLOCKED | YES | YES | ✅ | |
| 5 | state ≠ FAIL_FAST && ≠ LOST, res ≠ 0, state == BLOCKED | YES | NO | ❌ leak | Leak |
| 6 | state == FAIL_FAST, res == 0 | NO | YES | ❌ excess put | Block skipped, unblock always called |
| 7 | state == FAIL_FAST, res ≠ 0, state ≠ RUNNING && ≠ BLOCKED | NO | YES | ❌ excess put | |
| 8 | state == FAIL_FAST, res ≠ 0, state == RUNNING | NO | NO | ✅ | No unblock, no excess |
| 9 | state == FAIL_FAST, res ≠ 0, state == BLOCKED | NO | NO | ✅ | |
| 10 | state == LOST, res = -ENODEV (state unchanged) | NO | YES | ❌ excess put | Block skipped, unblock in else-if (LOST ≠ BLOCKED) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When rport->state is FAIL_FAST or LOST, scsi_block_targets() is skipped, but later scsi_target_unblock() is called unconditionally on success or on certain error paths, causing an extra kref_put on sdev_gendev.
```
