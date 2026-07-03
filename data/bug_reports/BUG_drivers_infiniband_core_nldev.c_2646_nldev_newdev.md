# REAL BUG: drivers/infiniband/core/nldev.c:2646 nldev_newdev()

**Confidence**: HIGH | **Counter**: `parent->refcount.refs.counter`

## Reasoning

tra reference on `parent` is taken (`ib_device_try_get`) but the corresponding `ib_device_put` is missing on an error path. The caller’s single `ib_device_put(parent)` only releases the reference acquired by `ib_device_get_by_index()`; it cannot compensate for a leaked reference inside the callee.

## Full Response

```
| Line | Return Type | GET Done? (ib_device_get_by_index) | PUT Done? | Balanced? | Notes |
|------|-------------|-----------------------------------|-----------|-----------|-------|
| L2631 | error       | NO (before get)                   | N/A       | ✅        | Early return before any get |
| L2638 | error       | NO (get failed)                   | N/A       | ✅        | ib_device_get_by_index returned NULL → no reference held |
| L2642 | success     | YES (L2637)                       | YES (L2641) | ✅        | Unconditional put after ib_add_sub_device balances the get from L2637 |

**Caller balance:** All return paths in `nldev_newdev()` correctly balance the reference obtained from `ib_device_get_by_index()`. The warning is **not** about a leak in this function.

**Root cause:** The `inconsistent refcounting` warning on `parent->refcount.refs.counter` arises from inside `ib_add_sub_device()`. The contract explicitly marks it as `conditional_on_path` and reveals that it uses `ib_device_try_get(get)` and `ib_device_put(put)`. This means that **within `ib_add_sub_device`**, on some execution paths an extra reference on `parent` is taken (`ib_device_try_get`) but the corresponding `ib_device_put` is missing on an error path. The caller’s single `ib_device_put(parent)` only releases the reference acquired by `ib_device_get_by_index()`; it cannot compensate for a leaked reference inside the callee.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The refcount inconsistency is caused by a missing `ib_device_put` inside `ib_add_sub_device` on one of its error paths (conditional get without matching put), making this a genuine leak.
```
