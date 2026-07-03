# REAL BUG: drivers/infiniband/hw/irdma/utils.c:784 irdma_handle_cqp_op()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| Inside waiting block, wait_event succeeds, return 0 | return 0 | YES | NO (put_cqp_request=false) | ✅ Intended | Ownership likely transferred to completion context |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L748 (if rf->reset) | return -EBUSY | NO (before get) | N/A | ✅ | |
| L756 (status != 0) goto err | goto err | YES | YES (put_cqp_request=true) | ✅ | |
| L765 (cqp_request->waiting) false, return 0 | return 0 | YES | NO | ❌ LEAK | put_cqp_request still true, no put called before return |
| Inside waiting block, put_cqp_request=false then wait_event fails, goto err | goto err | YES | NO (put_cqp_request=false) | ⚠️ Potential leak | If wait_event failed, ref may never be released; unclear if callee handles it, but main bug is the above |
| Inside waiting block, wait_event succeeds, return 0 | return 0 | YES | NO (put_cqp_request=false) | ✅ Intended | Ownership likely transferred to completion context |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Return L765 after unconditional `irdma_get_cqp_request` with `cqp_request->waiting` false fails to call `irdma_put_cqp_request`; the `put_cqp_request` flag remains true but no put is executed.
```
