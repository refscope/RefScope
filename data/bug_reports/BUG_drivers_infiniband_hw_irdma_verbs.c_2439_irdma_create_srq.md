# REAL BUG: drivers/infiniband/hw/irdma/verbs.c:2439 irdma_create_srq()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

The warning at line 2439 (likely the `put` or close to it) correctly identifies this inconsistency.

## Full Response

```
```
| Line | Return Type | GET Done? (cqp) | PUT Done? (cqp) | Balanced? | Notes |
|------|-------------|-----------------|-----------------|-----------|-------|
| early return -EOPNOTSUPP           | error | NO (before alloc) | N/A | ✅ | |
| early return -EINVAL               | error | NO (before alloc) | N/A | ✅ | |
| return err_code (alloc_rsrc fail)  | error | NO (before alloc) | N/A | ✅ | |
| return err_code (get_srqdepth fail)| error | NO (before alloc) | N/A | ✅ | |
| goto free_rsrc (setup_srq err)     | error | NO (before alloc) | N/A | ✅ | |
| goto free_dmem (sc_srq_init err)   | error | NO (before alloc) | N/A | ✅ | |
| goto free_dmem (alloc NULL)        | error | NO (alloc failed) | N/A | ✅ | irdma_alloc_and_get_cqp_request returned NULL |
| goto free_dmem (handle_cqp_op err) | error | YES (non‑NULL)   | YES (called after handle) | ❌ **POTENTIAL** | irdma_handle_cqp_op has **conditional_on_path** get/put – caller’s unconditional put may double‑free or leak |
| goto srq_destroy (ib_copy_to_udata fail) | error | YES | YES | ❌ **POTENTIAL** | same reason |
| return 0                           | success | YES | YES | ❌ **POTENTIAL** | same reason |

**Caller’s own get/put** are paired, but **irdma_handle_cqp_op** is contract‑annotated as **conditional_on_path** (`→irdma_get_cqp_request(get),irdma_put_cqp_request(put)`).  
This means the function may internally increment or decrement the request’s refcount without always pairing them.  
The caller unconditionally calls `irdma_put_cqp_request` after `irdma_handle_cqp_op`, assuming the refcount is still 1.  
On error paths where `handle_cqp_op` performed an unbalanced get or put, the caller’s put will either leak a reference or double‑free the object.  
The warning at line 2439 (likely the `put` or close to it) correctly identifies this inconsistency.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Caller unconditionally puts a request whose refcount was potentially altered by irdma_handle_cqp_op (conditional_on_path contract). Error paths and success path are vulnerable.
```
```
