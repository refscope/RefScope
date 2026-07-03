# REAL BUG: net/xfrm/xfrm_device.c:346 xfrm_dev_state_add()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

| L324 | success | YES (original + tracker) | NO explicit put (tracker put deferred, original never put) | ❌ LEAK | State holds both refs; cleanup via netdev_put only releases tracker, leaving original unreleased. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L237 | error (before any get) | NO | NO | ✅ | Early validation |
| L242 | error | NO | NO | ✅ | |
| L247 | error | NO | NO | ✅ | |
| L251 | error (x->tfcpad) | NO | NO | ✅ | |
| L270 | error / success (is_packet_offload flag) | NO (dev_get_by_index returned NULL, dst lookup error, no dev_hold) | NO | ✅ | No reference taken |
| L280 | conditional (is_packet_offload) | YES (via dev_get_by_index or dev_hold) | YES (dev_put) | ✅ | Balanced |
| L288 | error (ESN) | YES | YES (dev_put) | ✅ | Balanced |
| L293 | error (no type_offload) | YES | YES (dev_put) | ✅ | Balanced |
| L320 | error (after xdo_dev_state_add) | YES (original ref + tracker ref) | PARTIAL (netdev_put releases tracker only) | ❌ LEAK | Original reference never released; double‑get (original + tracker) with only one put. |
| L324 | success | YES (original + tracker) | NO explicit put (tracker put deferred, original never put) | ❌ LEAK | State holds both refs; cleanup via netdev_put only releases tracker, leaving original unreleased. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`netdev_tracker_alloc()` increments the device refcount (tracker ref), but the existing reference from `dev_get_by_index()`/`dev_hold()` is never released. In error paths after the alloc, only `netdev_put()` is called, leaking the original ref. On success, the state retains two refs but only the tracker is accounted for in future cleanup, leaking the original reference.
```
