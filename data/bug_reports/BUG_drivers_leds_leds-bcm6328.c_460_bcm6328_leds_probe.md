# REAL BUG: drivers/leds/leds-bcm6328.c:460 bcm6328_leds_probe()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

Without the callee source we cannot pinpoint the exact line, but the observed kref inconsistency is a concrete bug — the code will double-put the node on any error returned from the child.

## Full Response

```
| Line | Return Type | GET Done? (child) | PUT Done? (child) | Balanced? | Notes |
|------|-------------|-------------------|--------------------|-----------|-------|
| L403 (IS_ERR mem) | error | NO (before loop) | N/A | ✅ | |
| L407 (!lock) | error | NO | N/A | ✅ | |
| L412 (!blink_leds) | error | NO | N/A | ✅ | |
| L417 (!blink_delay) | error | NO | N/A | ✅ | |
| L460 (`if (rc < 0) return rc;`) | early error from loop | YES (by `for_each_available_child_of_node_scoped` macro) | YES (scoped cleanup `__free(of_node_put)` runs on return) | ✅ from this function’s local get/put, but **global refcount is imbalanced** because the callee (`bcm6328_hwled`/`bcm6328_led`) decremented the child’s kref via `of_node_put`, leading to the “excess put” at cleanup. | Warning line; the callee’s illegal put causes the scoped put to operate on a zero refcount, triggering the `kref` excess‑put report. |
| L462 (`return 0;`) | success | NO (loop ends with `child == NULL`, no ref held) | N/A | ✅ | |

**Reasoning**:  
The function itself uses a correct `for_each_available_child_of_node_scoped` pattern — every iteration acquires a reference and releases it automatically via `__free(of_node_put)`. The early exit at line 460 is properly cleaned up by the scoped destructor.  

The “excess put” warning on `$->kobj.kref.refcount.refs.counter` (the device node’s `kref`) at line 460 indicates that **before** the scoped cleanup runs, the reference count has already been decremented to zero by one of the called functions — most likely `bcm6328_led()` or `bcm6328_hwled()` calling `of_node_put(child)` erroneously. This makes the subsequent auto-put an extra decrement, a real refcount bug even though the caller’s own ref logic is sound.

Without the callee source we cannot pinpoint the exact line, but the observed kref inconsistency is a concrete bug — the code will double-put the node on any error returned from the child.  

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
Callee (`bcm6328_led`/`bcm6328_hwled`) likely does an unintended `of_node_put`, causing the scoped put at line 460 to hit a zero refcount.
```
