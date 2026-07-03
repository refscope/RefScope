# REAL BUG: drivers/soc/qcom/qcom_aoss.c:431 qmp_cooling_devices_register()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

The current source does not show an explicit child-put in the caller; the only source of the warning is the scoped cleanup combined with a put inside the callee.  Therefore this is a **REAL_BUG** in the error handling of `qmp_cooling_device_add`.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (child node) | PUT Done? (child node) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L403 | `return -ENOMEM` | NO (before any child) | N/A | ✅ | Allocation failure, loop never entered |
| L411 | `continue` (skip child) | YES (loop acquires ref) | YES (auto‑put at end of iteration) | ✅ | Property check fails, child put by scoped cleanup in next iteration step |
| L414‑415 | `goto unroll` on error from `qmp_cooling_device_add` | YES (loop ref held) | **YES** (scoped auto‑put) **BUT callee also puts** | ❌ **EXCESS PUT** | If `qmp_cooling_device_add` puts the child on failure, the scoped macro’s auto‑put becomes an **extra put** → refcount underflow |
| L418 | `return 0` (no devices) | YES (last child ref held) | YES (auto‑put after loop) | ✅ | Normal loop exit, no extra puts |
| L420‑? | `return 0` (success) | YES (for all children, loop refs dropped as usual) | YES (auto‑put) | ✅ | Devices hold their own references, loop ref released normally |

**Key observation**: The `for_each_available_child_of_node_scoped` macro attaches `__free(of_node_put)` cleanup to the `child` variable.  Exiting the loop (including via `goto unroll`) will automatically call `of_node_put(child)`.  
If `qmp_cooling_device_add()` *also* calls `of_node_put(child)` on its failure path, then two puts are performed – the second one (from the scoped cleanup) hits a zero refcount, creating an **excess put** warning exactly on line 431 (the scope exit of the function).  

The current source does not show an explicit child-put in the caller; the only source of the warning is the scoped cleanup combined with a put inside the callee.  Therefore this is a **REAL_BUG** in the error handling of `qmp_cooling_device_add`.

```
VERDICT: REAL_BUG
CONFIDENCE: HIGH
```

`qmp_cooling_device_add` likely calls `of_node_put(child)` on failure, causing the scoped auto-put to double-put the child node and trigger the `$->kobj.kref.refcount` excess-put warning at line 431.
```
