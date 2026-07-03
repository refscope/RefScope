# REAL BUG: block/bdev.c:787 blkdev_get_part()

**Confidence**: LOW | **Counter**: `$->bd_openers.counter`

## Reasoning

[NEED_SOURCE] blkdev_put_whole

## Full Response

```
| Line | Return Type | GET Done? (part->bd_openers) | PUT Done? (part->bd_openers) | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L772 | error (ret != 0) | NO (before atomic_inc) | NO (no put) | ✅ | blkdev_get_whole failed |
| L776→L786 | error (goto out_blkdev_put) | NO (atomic_inc omitted) | YES (blkdev_put_whole likely puts bd_openers) | ❌ EXCESS PUT | No get, but put executed |
| L783 | success (return 0) | YES (atomic_inc at L782) | NO (put deferred to close) | ✅ | caller will release |

[NEED_SOURCE] blkdev_put_whole

VERDICT: REAL_BUG
CONFIDENCE: LOW
blkdev_put_whole likely decrements part->bd_openers counter on the sectors-zero error path where no atomic_inc was performed, causing excess put.
```
