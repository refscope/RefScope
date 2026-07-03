# REAL BUG: drivers/dma/ti/omap-dma.c:1847 omap_dma_probe()

**Confidence**: MEDIUM | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

~1869) **does** call `dma_async_device_unregister()`, releasing those references. This makes the refcount handling **inconsistent** across the two error exits – one leaks, the other releases. Smatch flags this inconsistency at the final `return rc;` (line 1847 in the original file).

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~1662 | error | NO | N/A | ✅ | `od = devm_kzalloc` failed; no resources |
| ~1668 | error | NO | N/A | ✅ | `IS_ERR(od->base)`; before any get |
| ~1676 | error | NO | N/A | ✅ | `!od->plat` (conf branch) |
| ~1683 | error | NO | N/A | ✅ | `!od->plat` (OMAP1 branch) |
| ~1685 | error | NO | N/A | ✅ | else return ENODEV |
| ~1752 | goto err | NO | N/A | ✅ | `!od->lch_map`; early allocation fail |
| ~1758 | error | NO | N/A | ⚠️ | `omap_dma_chan_init` fail → `omap_dma_free(od)`; channel refs unknown; see note |
| ~1773 | error | NO | N/A | ⚠️ | IRQ fail; `omap_dma_free(od)`; same as above |
| ~1844 (dma_async_device_register fail) | error | **UNCERTAIN** | NO | ❌ | If `dma_async_device_register` partially got ref(s) before failing, ref LEAK; no `dma_async_device_unregister` called |
| ~1869 (of_dma_controller_register fail) | error (falls through to final) | YES (from successful register) | YES (`dma_async_device_unregister` called) | ✅ | Ref properly released; fall‑through to final `return rc` |
| ~1897 (success) | success | YES | NO (intentional, held for lifetime) | ✅ | Normal probe success path |

## What Smatch Found

Smatch tracks a kref on `$->ref.refcount.refs.counter`. The `GET` is triggered by `dma_async_device_register()`, whose contract says **conditional_on_path**. This means the function sometimes takes references even when it eventually returns an error (e.g., it does `kref_init` / `dma_chan_get` early, but then hits an error later and does not roll back all references).  
In the error path when `dma_async_device_register` returns non‑zero (line ~1844), the probe does **not** call `dma_async_device_unregister()`. If any references were taken on that path, they leak.  
Meanwhile, the subsequent error path for `of_dma_controller_register` failure (line ~1869) **does** call `dma_async_device_unregister()`, releasing those references. This makes the refcount handling **inconsistent** across the two error exits – one leaks, the other releases. Smatch flags this inconsistency at the final `return rc;` (line 1847 in the original file).

## Verdict

**VERDICT: REAL_BUG**  
**CONFIDENCE: MEDIUM**  
The `dma_async_device_register` failure path omits `dma_async_device_unregister()`, which leaks refcounts if the function took any references before failing (as implied by the “conditional_on_path” contract). The `of_dma_controller_register` failure path shows that `unregister` is the correct cleanup, so the omission is inconsistent and a genuine leak. Confidence is MEDIUM only because we haven’t inspected the internal implementation of `dma_async_device_register` to confirm that it does leave a reference on at least one error path.
```
