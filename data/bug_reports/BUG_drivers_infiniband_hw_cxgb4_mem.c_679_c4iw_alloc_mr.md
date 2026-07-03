# REAL BUG: drivers/infiniband/hw/cxgb4/mem.c:679 c4iw_alloc_mr()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| success (return `&(mhp->ibmr)`) | success | YES | NO (ownership transferred to MR) | ✅ | The `wr_waitp` ref is held by the MR object and will be released when the MR is deregistered later |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L614 (invalid `mr_type` or `max_num_sg`) | error `-EINVAL` | NO (before get) | N/A | ✅ | |
| `kzalloc` mhp fail → goto `err` | error `-ENOMEM` | NO (before get) | N/A | ✅ | |
| `c4iw_alloc_wr_wait` returns NULL → goto `err_free_mhp` | error `-ENOMEM` | NO (get failed) | N/A | ✅ | No ref held, no put needed |
| `dma_alloc_coherent` fail → goto `err_free_wr_wait` | error | YES (get succeeded) | YES (`c4iw_put_wr_wait` at `err_free_wr_wait`) | ✅ | |
| `alloc_pbl` fail → goto `err_free_dma` | error | YES | YES (falls through to `err_free_wr_wait`, then put) | ✅ | |
| `allocate_stag` fail → goto `err_free_pbl` | error | YES | YES (falls through to put via `err_free_wr_wait`) | ✅ | |
| `xa_insert_irq` fail → goto `err_dereg` | error | YES | YES (but **double put**) | ❌ **EXCESS PUT** | `dereg_mem` consumes `wr_waitp` (transfers ownership), then execution falls through to `err_free_wr_wait` which calls `c4iw_put_wr_wait` again |
| success (return `&(mhp->ibmr)`) | success | YES | NO (ownership transferred to MR) | ✅ | The `wr_waitp` ref is held by the MR object and will be released when the MR is deregistered later |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
On the `err_dereg` path, `dereg_mem` takes ownership of `mhp->wr_waitp` (it will call `c4iw_put_wr_wait` internally upon completion), but the function then falls through to the `err_free_wr_wait` label and calls `c4iw_put_wr_wait` again, causing an excess put on the `wr_waitp` kref.
```
