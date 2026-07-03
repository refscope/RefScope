# REAL BUG: drivers/infiniband/hw/vmw_pvrdma/pvrdma_qp.c:427 pvrdma_create_qp()

**Confidence**: HIGH | **Counter**: `qp->refcnt.refs.counter`

## Reasoning

| 349 | return 0 (success) | YES | N/A (caller holds ref) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 210 | return -EOPNOTSUPP | NO (before get) | N/A | ✅ | |
| 215 | return -EOPNOTSUPP | NO (before get) | N/A | ✅ | |
| 220 | return -EINVAL | NO (before get) | N/A | ✅ | |
| 224 | return -ENOMEM | NO (before get) | N/A | ✅ | |
| 231 | goto err_qp | NO (before get) | N/A | ✅ | refcount_set not executed |
| 249 | goto err_qp | YES | NO | ❌ LEAK | ib_copy_validate_udata_in fail; err_qp has no put |
| 255 | goto err_qp | YES | NO | ❌ LEAK | udata->outlen check fail |
| 262 | goto err_qp | YES | NO | ❌ LEAK | IS_ERR(qp->rumem) |
| 275 | goto err_qp | YES | NO | ❌ LEAK | IS_ERR(qp->sumem) |
| 281 | goto err_qp | YES | NO | ❌ LEAK | pvrdma_set_sq_size fail (kernel path) |
| 285 | goto err_qp | YES | NO | ❌ LEAK | pvrdma_set_rq_size fail (kernel path) |
| 292 | goto err_umem | YES | NO | ❌ LEAK | err_umem falls through to err_qp |
| 298 | goto err_umem | YES | NO | ❌ LEAK | pvrdma_page_dir_init fail; err_umem falls through |
| 309 | goto err_qp (default) | NO (before get) | N/A | ✅ | switch default, no refcount_set |
| 329 | goto err_pdir | YES | NO | ❌ LEAK | pvrdma_cmd_post fail; err_pdir falls through |
| 344 | return -EINVAL | YES | YES (__pvrdma_destroy_qp) | ✅ | udata copy fail after QP fully created |
| 349 | return 0 (success) | YES | N/A (caller holds ref) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`refcount_set(&qp->refcnt, 1)` at L239 is unconditional; multiple error paths after it (L249, L255, L262, L275, L281, L285, L292, L298, L329) jump to labels that never call `__pvrdma_destroy_qp()`, leaking the initial reference.
```
