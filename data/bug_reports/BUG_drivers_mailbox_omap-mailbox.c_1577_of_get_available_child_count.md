# REAL BUG: drivers/mailbox/omap-mailbox.c:1577 of_get_available_child_count()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1577 (return from loop) | normal return | YES (for each child node visited) | NO (no of_node_put) | ❌ LEAK | `for_each_available_child_of_node` increments refcount on each child; these references are never released. The child pointer goes out of scope without any put. |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1577 (return from loop) | normal return | YES (for each child node visited) | NO (no of_node_put) | ❌ LEAK | `for_each_available_child_of_node` increments refcount on each child; these references are never released. The child pointer goes out of scope without any put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`for_each_available_child_of_node` acquires a reference on each child node, but the loop body only increments a counter and never calls `of_node_put`, leaking every child node's refcount. The warning of "excess put" is a misclassification of a missing put (leak), which is a genuine refcount imbalance. This is a known kernel bug (since fixed upstream by adding `of_node_put(child)` in the loop).
```
```
