# REAL BUG: drivers/pinctrl/pinctrl-th1520.c:548 th1520_pinctrl_dt_node_to_map()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

Without the source of `th1520_pinctrl_dt_free_map()`, the exact mechanism (likely a call to `pinmux_generic_remove_function` or `put_device`) cannot be shown here, but the logical flaw is clear from the control flow.

## Full Response

```
## Analysis

The warning reports a **refcount excess put** on `$->kobj.kref.refcount.refs.counter` at line 548 of `drivers/pinctrl/pinctrl-th1520.c`. The line corresponds to the call to `th1520_pinctrl_dt_free_map()`. This function is the error‑handling cleanup for the pin‑map building function. The imbalance is not a missing put, but a **double‑put** (or put without a corresponding get) of a kref inside the free‑map helper. The root cause: `th1520_pinctrl_dt_free_map()` is called with a map that may contain `MUX_GROUP` entries for a child node whose `pinmux_generic_add_function()` was **never successfully called** – yet the free‑map function likely still attempts to clean up those entries, causing an extra `kref_put` on the pinctrl device’s kobject.

## Path Table

All return paths in `th1520_pinctrl_dt_node_to_map()`:

| Line | Return Type   | GET (kref from pinmux_generic_add_function) Done? | PUT (in free_map) Done? | Balanced? | Notes |
|------|---------------|---------------------------------------------------|-------------------------|-----------|-------|
| L436 | `-EINVAL`     | NO (before map alloc, first loop)                 | N/A                     | ✅        | No map built |
| L443 | `-ENOMEM`     | NO (before map build)                             | N/A                     | ✅        | | 
| L468 | `goto free_map` (→ L547 free_map) | NO (error before inner loop for **this child**, but `pinmux_generic_add_function` **not called** for any map entries of the current child, though earlier children may have added functions. For the current child’s entries, GET=NO.) | YES (free_map is called and will attempt to undo ALL mux entries including those for the current child that were never added) | ❌ **EXCESS PUT** | free_map tries to put kref for function entries that were never added → underflow |
| L473 | `goto free_configs` → `free_map` | NO (before inner loop, no mux entries for this child yet; earlier children may have added functions, but this child’s entries GET=NO) | YES (free_map tries to clean) | ❌ | Same reasoning |
| L478 | `goto free_configs` → `free_map` | NO (same as above) | YES | ❌ | |
| L483 | `goto free_configs` → `free_map` | NO (same as above) | YES | ❌ | |
| L504 | `goto free_configs` → `free_map` | NO (error **inside** inner loop; map entries for current child exist but `pinmux_generic_add_function` was **not called** for this child because the loop didn’t finish) | YES | ❌ | Critical: MUX_GROUP entries exist for this child, but the function was never added → free_map will issue a matching put without a get |
| L533 | `goto free_map` | NO (`pinmux_generic_add_function` **failed**, so no kref taken) | YES | ❌ | Even though the add failed, free_map still tries to clean the MUX_GROUP entries |
| L540 | `return 0`    | YES (all children successfully processed, function added for each) | N/A (normal return, no immediate free_map) | ✅ | |

All error paths that reach `free_map` after map entries have been created for a child (
```
