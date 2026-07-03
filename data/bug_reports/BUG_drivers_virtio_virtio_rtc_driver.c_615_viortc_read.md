# REAL BUG: drivers/virtio/virtio_rtc_driver.c:615 viortc_read()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L599 (fallthrough to out_release on success) | success (ret==0) | YES (init) | YES (inside viortc_msg_xfer) + YES (viortc_msg_release at L615) | ❌ EXCESS PUT | Same double put on the success path. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L592 (after VIORTC_MSG_INIT error) | error | YES (refcount_set from viortc_msg_init) | NO  | ❌ LEAK | No matching put; but not the reported excess put. |
| L595 (goto out_release after viortc_msg_xfer error) | error | YES (init) | YES (inside viortc_msg_xfer) + YES (viortc_msg_release at L615) | ❌ EXCESS PUT | viortc_msg_xfer unconditionally calls viortc_msg_release; out_release calls it again → double put. |
| L599 (fallthrough to out_release on success) | success (ret==0) | YES (init) | YES (inside viortc_msg_xfer) + YES (viortc_msg_release at L615) | ❌ EXCESS PUT | Same double put on the success path. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`viortc_msg_xfer` (unconditional PUT → `viortc_msg_release`) already releases a reference; the subsequent `viortc_msg_release` at `out_release` (line 615) causes an excess double put on both error and success paths.
```
