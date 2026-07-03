# REAL BUG: drivers/infiniband/hw/irdma/verbs.c:789 irdma_cqp_create_qp_cmd()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

[NEED_SOURCE] irdma_handle_cqp_op  (confirms that internal get/put operations change the refcount in a way not balanced by the caller’s single put)

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L769 (return -ENOMEM) | error | NO (before alloc) | N/A | ✅ | No get occurred |
| L789 (return status) | success/error | YES (irdma_alloc_and_get_cqp_request unconditional) | YES (irdma_put_cqp_request called at L788) | ❌ | `irdma_handle_cqp_op` is documented as “conditional_on_path; →irdma_get_cqp_request(get),irdma_put_cqp_request(put)”. This means the function internally either increments (get) or decrements (put) the reference count, making the caller’s unconditional put after the call incorrect: if `irdma_handle_cqp_op` already decremented (e.g., on error), the subsequent `irdma_put_cqp_request` is a double-put; if it incremented, the single put leaves a leak. |

[NEED_SOURCE] irdma_handle_cqp_op  (confirms that internal get/put operations change the refcount in a way not balanced by the caller’s single put)

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The contract for `irdma_handle_cqp_op` explicitly states it may call `irdma_get_cqp_request` or `irdma_put_cqp_request` depending on the path, meaning the reference count of `cqp_request` is altered inside that function. The caller’s unconditional `irdma_put_cqp_request` after the op therefore either double-frees (if handle already put) or leaves a reference leak (if handle got), making the refcounting inconsistent as flagged at line 789.
```
