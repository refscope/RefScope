# REAL BUG: drivers/infiniband/hw/usnic/usnic_uiom.c:414 usnic_uiom_reg_get()

**Confidence**: MEDIUM | **Counter**: `uiomr->owning_mm->mm_count.counter`

## Reasoning

es the `owning_mm`), the explicit `mmdrop` at L414 becomes an excess put. That is the most likely explanation, as otherwise the function’s refcounting appears balanced. Without the source of `usnic_uiom_put_pages` the exact cause cannot be confirmed, but the pattern strongly suggests a double‑put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L336 (alloc fail) | error, return ERR_PTR | NO (get_pages not called) | N/A | ✅ | No mm reference |
| L346 (get_pages fail) | error, goto out_free_uiomr | NO (get_pages failed) | N/A | ✅ | No mm acquired |
| L354 (intervals_diff fail) | error, goto out_put_pages | YES (get_pages succeeded) | YES (mmdrop at L414, after put_pages) | ⚠️ If `usnic_uiom_put_pages` also drops mm → DOUBLE PUT (excess) | `out_put_pages` calls `usnic_uiom_put_pages`, spin_unlock, mmdrop |
| L360 (map_intervals fail) | error, goto out_put_intervals | YES | YES (via out_put_pages) | ⚠️ same double‑put risk | path: out_put_intervals → out_put_pages → mmdrop |
| L366 (insert_interval fail) | error, goto out_unmap_intervals | YES | YES (via out_put_pages) | ⚠️ same risk | path: out_unmap_intervals → out_put_intervals → out_put_pages → mmdrop |
| L371 (success) | return uiomr | YES | NO (caller will put) | ✅ | Reference retained; caller releases later |

[NEED_SOURCE] usnic_uiom_put_pages
[NEED_SOURCE] usnic_uiom_get_pages

**Analysis**:  
The warning “excess put” on `mmdrop(uiomr->owning_mm)` at L414 implies the counter went negative when this `mmdrop` executed. All error paths after a successful `usnic_uiom_get_pages` (which presumably takes an mm reference) converge to the label `out_put_pages`, which calls `usnic_uiom_put_pages` *and then* `mmdrop`. If `usnic_uiom_put_pages` internally also calls `mmdrop` (or otherwise releases the `owning_mm`), the explicit `mmdrop` at L414 becomes an excess put. That is the most likely explanation, as otherwise the function’s refcounting appears balanced. Without the source of `usnic_uiom_put_pages` the exact cause cannot be confirmed, but the pattern strongly suggests a double‑put.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`usnic_uiom_put_pages` likely already drops the mm reference, making the `mmdrop` at L414 on error paths a double put.
```
