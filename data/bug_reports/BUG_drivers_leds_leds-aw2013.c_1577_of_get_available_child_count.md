# REAL BUG: drivers/leds/leds-aw2013.c:1577 of_get_available_child_count()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1577 | success     | YES (multiple) | NO   | ❌ LEAK | `for_each_available_child_of_node` calls `of_get_next_available_child` for each child, incrementing each child’s refcount; no `of_node_put` is called in the loop or after it – all references are leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1577 | success     | YES (multiple) | NO   | ❌ LEAK | `for_each_available_child_of_node` calls `of_get_next_available_child` for each child, incrementing each child’s refcount; no `of_node_put` is called in the loop or after it – all references are leaked |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The loop increments the refcount of every available child via `of_get_next_available_child` but never releases any of them, causing a refcount leak for each child node.
```
