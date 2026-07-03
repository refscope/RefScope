# REAL BUG: drivers/leds/leds-mc13783.c:1577 of_get_available_child_count()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1577 | return num (no children)      | NO (first call returns NULL, no ref taken) | N/A       | ✅        | No children exist, so no reference is ever obtained.                                                                                                   |

## Full Response

```
| Line | Return Type        | GET Done? | PUT Done? | Balanced? | Notes                                                                                                                                                  |
|------|--------------------|-----------|-----------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| L1577 | return num (children present) | YES (references taken by `for_each_available_child_of_node` on all children) | NO (no `of_node_put` in function) | ❌ LEAK   | Each child gets its refcount incremented; overwriting the loop variable discards the reference without release. All child refs leaked. |
| L1577 | return num (no children)      | NO (first call returns NULL, no ref taken) | N/A       | ✅        | No children exist, so no reference is ever obtained.                                                                                                   |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The loop construct `for_each_available_child_of_node` obtains a reference on every child but the function never calls `of_node_put` on any of them, leaking all those references. The reported "excess put" warning likely stems from a later put that underflows the counter because the reference leaks were not properly balanced.
```
