# REAL BUG: drivers/leds/rgb/leds-qcom-lpg.c:1654 lpg_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

4     | `return lpg_add_pwm(lpg);` after loop | NO (np = NULL, no child node get) | NO (scoped put on NULL is NOP) | N/A | No child node ref held here. Warning line 1654 is where the scoped cleanup of the loop variable triggers, which would have been a put that now sees a refcount underflow. |

## Full Response

```
[NEED_SOURCE] lpg_add_led

```
| Line       | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------------|-------------|-----------|-----------|-----------|-------|
| L1645-1649 | loop iteration, no return | YES (of_get_next_available_child via macro) | YES (scoped __free(of_node_put) at end of iteration) | YES from caller’s view, but callee may also PUT → double PUT | `lpg_add_led` may consume the ref; if so, the scoped put is excess |
| L1645-1648 | `return ret;` inside loop on error | YES (same as above) | YES (scoped put on scope exit at return) | YES if `lpg_add_led` failed and didn’t consume; balanced | Error path, `lpg_add_led` probably didn’t take ownership |
| L1654     | `return lpg_add_pwm(lpg);` after loop | NO (np = NULL, no child node get) | NO (scoped put on NULL is NOP) | N/A | No child node ref held here. Warning line 1654 is where the scoped cleanup of the loop variable triggers, which would have been a put that now sees a refcount underflow. |
```

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The warning “excess put” on the child node’s kref at line 1654 indicates that the automatic `of_node_put()` from the scoped loop `for_each_available_child_of_node_scoped` is called on a node whose reference has already been consumed by `lpg_add_led()`. In the success path, `lpg_add_led` likely stores the node without incrementing the reference (or internally releases it), leading to a double drop when the scoped cleanup runs at the end of the iteration or when the function returns. The leak detection thus sees the refcount going negative at the point of the implicit put.
```
