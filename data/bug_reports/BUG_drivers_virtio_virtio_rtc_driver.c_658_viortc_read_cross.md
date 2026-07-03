# REAL BUG: drivers/virtio/virtio_rtc_driver.c:658 viortc_read_cross()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L647 success (ret==0) → fall through to L656 out_release → L658 release | success | YES (VIORTC_MSG_INIT succeeded → ref=1) | YES (viortc_msg_xfer released) → then **extra** viortc_msg_release at L658 | ❌ EXCESS PUT | Same double‑release on the success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L638 (return ret) | error | NO (init failed, no ref held) | N/A | ✅ | No msg created → no ref to release |
| L647‑L650 → goto out_release (xfer error) | error | YES (VIORTC_MSG_INIT succeeded → ref=1) | YES (viortc_msg_xfer released) → then **extra** viortc_msg_release at L658 | ❌ EXCESS PUT | xfer already consumed the reference; double‑release triggers refcount overflow |
| L647 success (ret==0) → fall through to L656 out_release → L658 release | success | YES (VIORTC_MSG_INIT succeeded → ref=1) | YES (viortc_msg_xfer released) → then **extra** viortc_msg_release at L658 | ❌ EXCESS PUT | Same double‑release on the success path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`viortc_msg_xfer` unconditionally releases the message (PUT), and the function immediately calls `viortc_msg_release` again — a guaranteed double‑free on every path that calls `viortc_msg_xfer`.
```
