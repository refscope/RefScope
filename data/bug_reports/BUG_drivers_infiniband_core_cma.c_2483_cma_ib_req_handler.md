# REAL BUG: drivers/infiniband/core/cma.c:2483 cma_ib_req_handler()

**Confidence**: HIGH | **Counter**: `net_dev->dev_refcnt.refs.counter`

## Reasoning

| goto err_unlock (all paths) | error | YES | YES (falls through to net_dev_put) | ✅ | err_unlock unlocks mutex then hits net_dev_put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| IS_ERR(listen_id) return | error | YES (unconditional) | NO | ❌ LEAK | cma_ib_id_from_event always grabs net_dev ref. Early return skips dev_put. |
| goto net_dev_put (after check_qp_type) | error | YES | YES (via net_dev_put) | ✅ | |
| goto err_unlock (all paths) | error | YES | YES (falls through to net_dev_put) | ✅ | err_unlock unlocks mutex then hits net_dev_put. |
| Normal fallthrough to err_unlock | success | YES | YES (via err_unlock) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
cma_ib_id_from_event unconditionally increments net_dev refcount (per contract), but the immediate return on IS_ERR(listen_id) does not call dev_put, leaking the reference.
```
