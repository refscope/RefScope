# REAL BUG: drivers/gpu/drm/etnaviv/etnaviv_drv.c:675 etnaviv_pdev_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

- The loop via `for_each_compatible_node` manages its own reference, but the extra reference taken by `drm_of_component_match_add` is left dangling on error.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L654 | error (-ENODEV) from dma_mask check | YES (via drm_of_component_match_add in DT loop) | NO | ❌ **LEAK** | Match list with node references created in the earlier `for_each_compatible_node` loop is leaked on this error path. No cleanup of `match` before return. |
| L662 | success/failure (return of component_master_add_with_match) | YES (same DT path) | ? (depends on framework) | UNCERTAIN | If `component_master_add_with_match` fails, it may or may not free the match; but the L654 path alone is a clear leak. |

**Analysis of L654:** The function first builds a `component_match` list, which for device-tree platforms calls `drm_of_component_match_add` that internally acquires a reference on each `core_node` via `of_node_get`. Then the code checks DMA capabilities. If those fail, the function returns `-ENODEV` at line 654 without any cleanup of the `match` list or its held node references. The references are never released, causing a kref leak on those device_node objects. The warning line 675 likely points to the function return or closing brace, and this gap is an obvious bug.

**Contract confirmation**:
- `drm_of_component_match_add`: unconditional get (stores reference in match).
- `etnaviv_of_first_available_node` is after the error path, so not involved here.
- The loop via `for_each_compatible_node` manages its own reference, but the extra reference taken by `drm_of_component_match_add` is left dangling on error.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`etnaviv_pdev_probe()` builds a component_match (taking node refs) before the DMA mask check; on DMA error it returns -ENODEV without releasing match or node references, leaking krefs.
```
