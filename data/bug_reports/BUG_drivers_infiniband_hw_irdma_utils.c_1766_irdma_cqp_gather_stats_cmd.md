# REAL BUG: drivers/infiniband/hw/irdma/utils.c:1766 irdma_cqp_gather_stats_cmd()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

The unconditional put at L1764 therefore creates an inconsistent refcounting state at function return (line 1766). This matches the smatch “inconsistent refcounting” warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1749 | error       | NO (cqp_request is NULL) | N/A | ✅ | alloc_and_get failed, no ref held |
| L1765 | success/error | YES (alloc_and_get succeeded at L1749) | YES (explicit put at L1764) | ⚠️ | `irdma_handle_cqp_op` may have already put the request → extra put on some paths |

**Breakdown**:  
- L1749: `irdma_alloc_and_get_cqp_request` returns NULL, no refcount taken, no put needed → balanced.
- L1765: The `irdma_alloc_and_get_cqp_request` call succeeded (refcount=1). After `irdma_handle_cqp_op`, the code **unconditionally** calls `irdma_put_cqp_request`.

**Why it’s not truly balanced**: The contract for `irdma_handle_cqp_op` states it is **conditional_on_path** and can call `irdma_get_cqp_request` and `irdma_put_cqp_request` internally. This means the net refcount after `irdma_handle_cqp_op` can be:
- **0** (if it consumed the initial reference, e.g., on success) → the caller’s `irdma_put_cqp_request` becomes a **double-free**.
- **1** (net neutral) → caller’s put is correct.
- **2** (if it added a reference for async processing) → caller’s single put **leaks one reference**.

The unconditional put at L1764 therefore creates an inconsistent refcounting state at function return (line 1766). This matches the smatch “inconsistent refcounting” warning.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`irdma_handle_cqp_op` conditionally modifies the request’s refcount; the caller must not put unconditionally after that call, otherwise paths where the callee already released the request lead to a double-free.
```
