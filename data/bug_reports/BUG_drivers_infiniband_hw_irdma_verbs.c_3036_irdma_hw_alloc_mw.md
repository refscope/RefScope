# REAL BUG: drivers/infiniband/hw/irdma/verbs.c:3036 irdma_hw_alloc_mw()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

_cqp_request`) | YES (explicit `irdma_put_cqp_request`) | ❌ **UNBALANCED** if `irdma_handle_cqp_op` already released the ref | Unconditional put after `irdma_handle_cqp_op`; contract shows that function can call `irdma_put_cqp_request` internally, making this an extra put on one or more paths |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3014(?) | error (–ENOMEM) | NO (alloc returned NULL) | N/A  | ✅ | early bail, no ref held |
| L3036(?) | success/error (after handle) | YES (from `irdma_alloc_and_get_cqp_request`) | YES (explicit `irdma_put_cqp_request`) | ❌ **UNBALANCED** if `irdma_handle_cqp_op` already released the ref | Unconditional put after `irdma_handle_cqp_op`; contract shows that function can call `irdma_put_cqp_request` internally, making this an extra put on one or more paths |

## VERDICT: REAL_BUG
CONFIDENCE: MEDIUM  
`irdma_handle_cqp_op` internally calls `irdma_put_cqp_request` (per contract), yet the caller unconditionally does another `irdma_put_cqp_request` right after – leading to a double‑put when the internal release already consumed the reference obtained from `irdma_alloc_and_get_cqp_request`.
```
