# REAL BUG: drivers/input/touchscreen/touchright.c:90 tr_disconnect()

**Confidence**: HIGH | **Counter**: `tr->dev->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L90  | void (implicit return) | YES (L84: input_get_device) | YES (L85: input_unregister_device implicitly does put; L88: input_put_device) | ❌ EXCESS PUT | one get, two puts: L85’s internal put (as per contract) + L88 explicit put cause double-decrement on kref. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L90  | void (implicit return) | YES (L84: input_get_device) | YES (L85: input_unregister_device implicitly does put; L88: input_put_device) | ❌ EXCESS PUT | one get, two puts: L85’s internal put (as per contract) + L88 explicit put cause double-decrement on kref. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
tr_disconnect() calls input_get_device (one get), then input_unregister_device (which internally puts), then input_put_device (second put); the double-decrement leads to an excess put and use-after-free risk.
```
