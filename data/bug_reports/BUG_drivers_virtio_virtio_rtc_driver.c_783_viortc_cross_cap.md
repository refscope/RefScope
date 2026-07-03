# REAL BUG: drivers/virtio/virtio_rtc_driver.c:783 viortc_cross_cap()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L777 (success, fall‑through to out_release) | fall‑through → release then return | YES (init) | YES (xfer) + YES (out_release) | ❌ EXCESS PUT | Same double‑put pattern |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L762 (init error) | immediate return | YES (viortc_msg_init is unconditional) | NO | ❌ LEAK | Warning not about this path, but still a ref leak |
| L770 (xfer error, goto out_release) | goto → release then return | YES (init) | YES (xfer executes release per contract) + YES (out_release release) | ❌ EXCESS PUT | viortc_msg_xfer already releases; explicit release is extra |
| L777 (success, fall‑through to out_release) | fall‑through → release then return | YES (init) | YES (xfer) + YES (out_release) | ❌ EXCESS PUT | Same double‑put pattern |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
viortc_msg_xfer unconditionally calls viortc_msg_release (contract), so the explicit viortc_msg_release at out_release (line 783) causes an excess put on the already zeroed refcount.
```
```
