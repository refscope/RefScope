# REAL BUG: drivers/pmdomain/core.c:3359 genpd_dev_pm_attach_by_id()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

- Therefore, every return path after `virt_dev->of_node = of_node_get(dev->of_node)` leaks the reference.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 3317 | `return NULL` | NO (before get) | N/A | ✅ | Before `of_node_get` |
| ~3323 | `return NULL` | NO (before get) | N/A | ✅ | Before `of_node_get` |
| ~3326 | `return ERR_PTR(-ENODEV)` | NO (before get) | N/A | ✅ | Before `of_node_get` |
| ~3330 | `return ERR_PTR(-ENOMEM)` | NO (before get) | N/A | ✅ | Before `of_node_get` |
| ~3341‑3343 | `put_device(virt_dev); return ERR_PTR(ret);` | YES | NO | ❌ LEAK | `of_node_get` already done; `put_device` eventually calls `genpd_release_dev`, which only `kfree`s – no `of_node_put` |
| ~3347‑3350 | `device_unregister(virt_dev); return ERR_PTR(ret)/NULL;` | YES | NO | ❌ LEAK | Same as above – `device_unregister` leads to `genpd_release_dev`, no `of_node_put` |
| ~3357 | `return virt_dev;` (success) | YES | NO | ❌ LEAK | Device returned to caller; when eventually `put_device` is called, release still does not put the `of_node` |

**Notes**:
- `of_node_get` is an **unconditional** GET per its contract – every return path after that line holds the reference.
- `put_device` / `device_unregister` are the only possible PUT paths for the device, but the device’s release function `genpd_release_dev` does **not** call `of_node_put`.  
  The typical kernel custom is to do `of_node_put(dev->of_node)` in the release handler, but here it is absent.
- No explicit `of_node_put` call exists anywhere in the function, nor in error cleanups outside the device release.
- Therefore, every return path after `virt_dev->of_node = of_node_get(dev->of_node)` leaks the reference.

## PRE-VERDICT CHECKLIST
1. **“Held for device lifetime”?** Not applicable – the warning is about a leak that persists even across device lifetime because no release path ever puts the node.
2. **“Ownership transferred”?** The reference is stored in `virt_dev->of_node`, but the receiver (device release) never releases it → transfer incomplete → LEAK.
3. **Unconditional GET?** `of_node_get` always increments – YES.
4. **goto out between GET and PUT?** No `goto` but there are direct returns after the get that skip any `of_node_put` – LEAK on those paths.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_node_get` acquires a reference that is never released in any return path, because the device’s release function `genpd_release_dev` lacks an `of_node_put`, making the refcount leak permanent.
```
