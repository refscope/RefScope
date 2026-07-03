# REAL BUG: drivers/pinctrl/pinctrl-at91-pio4.c:670 atmel_pctl_dt_node_to_map()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

ll be) dropped by the map‑freeing logic. This points to a missing `of_node_get()` inside `atmel_pctl_dt_subnode_to_map` when it stores the node pointer in the pin control map. Without that additional reference, the loop’s cleanup and the map’s cleanup conflict, causing the observed kref underflow.

## Full Response

```
[NEED_SOURCE] atmel_pctl_dt_subnode_to_map

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L664 | return ret  | No explicit get in this function | No explicit put | N/A (balance depends on callee and scoped loop) | The function itself has no direct `of_node_get`/`of_node_put` calls. The warning's refcount underflow is on a device_node whose get/put operations are driven by `for_each_child_of_node_scoped` and the semantics of `atmel_pctl_dt_subnode_to_map`. |

**Loop‑path specific analysis** (the real concern):

| Path | GET (`of_get_next_child` + `of_node_put` in iteration) | PUT triggered | Effect |
|------|-----------------------------------------------------------|---------------|--------|
| Normal loop exit (no more children) | `np` becomes NULL; cleanup is no-op | None | OK if map entries have their own references |
| Break on error (`ret < 0`) | `np` is the current child with a reference held by the loop | **1)** `__free(device_node)` cleanup calls `of_node_put(np)` **2)** later `pinctrl_utils_free_map` may call `of_node_put` on the same `np` if it was stored in the map without an additional `of_node_get` | **Excess put** (double-decrement) |

The warning at line 670 (`refcount excess put`) is triggered exactly by a double-put scenario: the scoped loop’s automatic cleanup drops the reference that was already (or will be) dropped by the map‑freeing logic. This points to a missing `of_node_get()` inside `atmel_pctl_dt_subnode_to_map` when it stores the node pointer in the pin control map. Without that additional reference, the loop’s cleanup and the map’s cleanup conflict, causing the observed kref underflow.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The scoped loop’s automatic `of_node_put` on break conflicts with `pinctrl_utils_free_map`’s likely `of_node_put` on the same node, unless the map‑building function explicitly takes an additional reference. The smatch warning and the control flow strongly suggest the map does **not** take that reference, leading to an excess put.
```
