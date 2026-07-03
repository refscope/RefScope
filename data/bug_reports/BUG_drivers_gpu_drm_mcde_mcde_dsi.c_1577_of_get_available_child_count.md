# REAL BUG: drivers/gpu/drm/mcde/mcde_dsi.c:1577 of_get_available_child_count()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

n imbalance of get/put pairs – the function acquires references without releasing them. This is a real refcount bug (reference leak). While the warning message may be mis-categorized by the static checker, the code is definitely buggy and can lead to memory leaks (device_node objects never freed).

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1575 (return num) | success     | YES (multiple calls to `of_get_next_available_child` inside `for_each_available_child_of_node`) | NO  | ❌ LEAK  | Each iteration calls `of_get_next_available_child` which increments the refcount of the returned node. The pointer `child` is overwritten on each iteration without calling `of_node_put`, leaking references to all children except the last. The final child’s reference is also never released because the function returns without putting it. |

## Analysis
- The macro `for_each_available_child_of_node` calls `of_get_next_available_child` (a **GET** operation) for every child and stores the result in `child`.
- The function does not call `of_node_put` (a **PUT** operation) at any point.
- All acquired references are leaked: earlier children’s pointers are overwritten without a put, and the last child’s pointer is discarded on return without a put.
- The warning reports an “excess put”, but the root cause is an imbalance of get/put pairs – the function acquires references without releasing them. This is a real refcount bug (reference leak). While the warning message may be mis-categorized by the static checker, the code is definitely buggy and can lead to memory leaks (device_node objects never freed).

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
