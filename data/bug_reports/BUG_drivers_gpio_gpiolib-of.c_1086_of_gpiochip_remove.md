# REAL BUG: drivers/gpio/gpiolib-of.c:1086 of_gpiochip_remove()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1086 (end of function after put) | void return | NO (np obtained via dev_of_node, no get) | YES (of_node_put(np)) | ❌ Excess put | dev_of_node returns borrowed pointer; put on node not owned by this function |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1086 (end of function after put) | void return | NO (np obtained via dev_of_node, no get) | YES (of_node_put(np)) | ❌ Excess put | dev_of_node returns borrowed pointer; put on node not owned by this function |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Function drops a reference on the chip’s device tree node without owning it. `dev_of_node` returns a pointer without incrementing the refcount, so `of_node_put(np)` releases a reference that was never taken, causing an excess put.
```
