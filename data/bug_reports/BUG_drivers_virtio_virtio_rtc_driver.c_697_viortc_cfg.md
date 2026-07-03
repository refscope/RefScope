# REAL BUG: drivers/virtio/virtio_rtc_driver.c:697 viortc_cfg()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L688 → out_release | fallthrough to out_release | YES | YES (via out_release) | ❌ EXCESS PUT | same double release on success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L679 | error       | NO (init failed, assumes no ref held) | NO | ✅ | Early return, no ref to put |
| L684 | goto out_release | YES (init succeeded, ref held) | YES (via out_release) | ❌ EXCESS PUT | `viortc_msg_xfer()` already did unconditional put, `out_release` does another put → double release |
| L688 → out_release | fallthrough to out_release | YES | YES (via out_release) | ❌ EXCESS PUT | same double release on success path |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`viortc_msg_xfer()` unconditionally performs `viortc_msg_release()` (per contract), but the caller unconditionally releases again via `out_release` label on both error and success paths, causing a double put and eventual refcount underflow.
```
