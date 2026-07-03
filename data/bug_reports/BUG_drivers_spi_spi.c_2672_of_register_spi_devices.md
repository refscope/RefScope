# REAL BUG: drivers/spi/spi.c:2672 of_register_spi_devices()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

via `of_get_next_available_child`) | YES (macro may `of_node_put` previous `nc` when advancing) | ❌ EXCESS PUT | `of_register_spi_device` calls `of_node_put` on `nc` (per contract), releasing caller’s reference. The macro then puts `nc` again on advance, causing double put → refcount underflow. |

## Full Response

```
 | Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| end of loop (implicit return after `for_each_available_child_of_node` advances and gets NULL) | normal exit | YES (on previous `nc` via `of_get_next_available_child`) | YES (macro may `of_node_put` previous `nc` when advancing) | ❌ EXCESS PUT | `of_register_spi_device` calls `of_node_put` on `nc` (per contract), releasing caller’s reference. The macro then puts `nc` again on advance, causing double put → refcount underflow. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`of_register_spi_device` unconditionally calls `of_node_put` on the device_node, releasing the caller's reference. The `for_each_available_child_of_node` macro often performs its own `of_node_put` on the old child when fetching the next, leading to a double release. The subsequent excess put triggers the reported refcount warning at the loop head (line 2672).
```
