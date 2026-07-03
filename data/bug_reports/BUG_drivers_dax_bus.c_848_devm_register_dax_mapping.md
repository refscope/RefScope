# REAL BUG: drivers/dax/bus.c:848 devm_register_dax_mapping()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L847 | error       | YES (parent ref) | NO   | ❌ LEAK | devm_add_action_or_reset fails, no parent put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L820 | error       | NO (before get) | N/A  | ✅ | |
| L824 | error       | NO (before get) | N/A  | ✅ | |
| L829 | error       | NO (before get) | N/A  | ✅ | |
| L841 | error       | YES (parent ref) | NO (child only) | ❌ LEAK | device_add fails; put_device(dev) releases child but not parent |
| L847 | error       | YES (parent ref) | NO   | ❌ LEAK | devm_add_action_or_reset fails, no parent put |
| L848 | success     | YES (parent ref) | YES (deferred) | ✅ | parent released via devm action unregister_dax_mapping |

VERDICT: REAL_BUG
CONFIDENCE: HIGH  
get_device(dev->parent) at L835 unconditionally increments parent refcount.  device_add failure (L841) and devm_add_action_or_reset failure (L847) return without releasing that reference, leaking it.
```
