# REAL BUG: drivers/regulator/as3722-regulator.c:632 as3722_get_regulator_dt_data()

**Confidence**: HIGH | **Counter**: `np->kobj.kref.refcount.refs.counter`

## Reasoning

| L632 | success (0)      | YES (np non‑NULL) | YES (`of_node_put(np)`) | ❌ Excess (external) | Same as above |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L600 | error (-ENODEV) | NO (np NULL) | N/A       | ✅ | `of_get_child_by_name` returned NULL |
| L610 | error (ret < 0) | YES (np non‑NULL) | YES (`of_node_put(np)`) | ❌ Excess (external) | After `pdev->dev.of_node = np` the device expects a reference, but this path puts it prematurely |
| L632 | success (0)      | YES (np non‑NULL) | YES (`of_node_put(np)`) | ❌ Excess (external) | Same as above |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The function drops `np`’s reference with `of_node_put()` immediately after storing the pointer in `pdev->dev.of_node`, leaving the device with a dangling pointer and creating an excess put from the perspective of the device’s expected reference hold. The put is unreferenced and must be removed, or replaced with `device_set_of_node()` that properly transfers the reference.
```
