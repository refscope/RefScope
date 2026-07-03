# REAL BUG: drivers/scsi/sg.c:1562 sg_add_device()

**Confidence**: HIGH | **Counter**: `scsidp->request_queue->refs.refs.counter`

## Reasoning

| L1558 | return 0 (success) | YES | YES (deferred) | ✅ | Reference held by device, released on removal |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1499 | error return | NO (get failed) | N/A | ✅ | `blk_get_queue` returned false |
| L1508 | goto out | YES | YES | ✅ | `out` label calls `blk_put_queue` |
| L1516 | goto out | YES | YES | ✅ | `out` label calls `blk_put_queue` |
| L1523 | goto cdev_add_err | YES | NO | ❌ LEAK | `cdev_add_err` lacks `blk_put_queue` |
| L1531 | goto cdev_add_err | YES | NO | ❌ LEAK | `cdev_add_err` lacks `blk_put_queue` |
| L1558 | return 0 (success) | YES | YES (deferred) | ✅ | Reference held by device, released on removal |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`sg_add_device` acquires a queue reference via `blk_get_queue`, but error paths going to `cdev_add_err` (cdev_add failure, device_create failure) skip `blk_put_queue`, leaking the reference.
```
