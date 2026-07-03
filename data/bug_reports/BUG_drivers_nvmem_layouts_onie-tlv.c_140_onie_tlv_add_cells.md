# REAL BUG: drivers/nvmem/layouts/onie-tlv.c:140 onie_tlv_add_cells()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

S (L104) | YES (L133)  | YES (if cell.np non‑NULL from a previous iteration) | NO (ownership transferred to nvmem cell) | ⚠️ (intentional transfer) | child ref held by added cell; nvmem core does not take extra ref, so the refcount is transferred – OK if error never happens; but error path leaks |

## Full Response

```
| Line | Return Type | GET layout? | PUT layout? | GET child? (cell.np) | PUT child? | Balanced? | Notes |
|------|-------------|-------------|-------------|----------------------|------------|-----------|-------|
| L105 | error -ENOENT | NO (layout NULL) | N/A         | NO                   | N/A        | ✅ | layout get failed, nothing to do |
| L129 | error (nvmem_add_one_cell failed) | YES (L104) | YES (L128)  | YES if of_get_child_by_name() returned non‑NULL (L123) | NO         | ❌ LEAK  | child ref acquired but never released on error – missing of_node_put(cell.np) |
| L113 → L135 | success (break → loop exit → return 0) | YES (L104) | YES (L133)  | NO (break before get) | N/A        | ✅ | no child get on this iteration |
| L120 → loop | continue (no return) | YES | N/A (loop keeps going) | NO (skipped) | N/A | ✅ (loop continues) | no child get |
| L135 | return 0 (after loop) | YES (L104) | YES (L133)  | YES (if cell.np non‑NULL from a previous iteration) | NO (ownership transferred to nvmem cell) | ⚠️ (intentional transfer) | child ref held by added cell; nvmem core does not take extra ref, so the refcount is transferred – OK if error never happens; but error path leaks |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`onie_tlv_add_cells()` acquires a reference via `of_get_child_by_name()` at L123, and if `nvmem_add_one_cell()` fails, the error path at L128‑L129 releases the `layout` node but leaks the child node reference. The reference must be dropped with `of_node_put(cell.np)` before returning, else a kref imbalance occurs whenever a child node exists and the cell addition fails.
```
