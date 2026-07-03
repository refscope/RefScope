# REAL BUG: drivers/virtio/virtio_rtc_driver.c:827 viortc_read_alarm()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L822 (success, out_release fall‑through) | success | YES (from init) | YES (xfer does put) + YES (explicit release at L820) | ❌ **EXCESS PUT** | Same double put; xfer consumes the reference, caller should not release again |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L804 | early error (VIORTC_MSG_INIT fails) | YES (unconditional refcount_set per contract) | NO | ❌ potential leak | Not flagged by warning; not the source of excess put |
| L813 (`goto out_release`) | error (viortc_msg_xfer fails) | YES (from init) | YES (xfer does put, unconditional) + YES (explicit viortc_msg_release at L820) | ❌ **EXCESS PUT** | Double free: xfer already releases, then out_release does a second put |
| L822 (success, out_release fall‑through) | success | YES (from init) | YES (xfer does put) + YES (explicit release at L820) | ❌ **EXCESS PUT** | Same double put; xfer consumes the reference, caller should not release again |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`viortc_msg_xfer()` contract shows it unconditionally calls `viortc_msg_release()` (PUT). After it returns (error or success), the explicit `viortc_msg_release()` at L820 causes a second put, resulting in a refcount underflow (excess put). The fix is to remove the explicit `viortc_msg_release()` after `viortc_msg_xfer()` has already handled the reference handoff.
```
