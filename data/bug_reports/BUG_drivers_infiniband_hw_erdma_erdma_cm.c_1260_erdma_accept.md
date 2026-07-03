# REAL BUG: drivers/infiniband/hw/erdma/erdma_cm.c:1260 erdma_accept()

**Confidence**: HIGH | **Counter**: `(0<~$0)->refcount.refs.counter`

## Reasoning

| success → return 0 | success (return) | YES (qp_get, cep_get, add_ref) | NO (references kept for connection lifetime) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| state != RECVD_MPAREQ → return -ECONNRESET | error (return) | NO (only initial get/put already balanced; no new gets) | YES (explicit put releases original cep reference) | ✅ | |
| qp == NULL → return -ENOENT | error (return) | NO (no extra gets) | NO (no cep_put) | ❌ LEAK | original cep reference leaked |
| state > RTR → goto error | error (goto) | YES (qp_get, and later cep_get + add_ref not yet done at this point) | YES (qp_put + final cep_put releases original reference) | ✅ | |
| ord/ird check → goto error | error (goto) | YES (qp_get, no cep_get/add_ref yet) | YES (qp_put + final cep_put) | ✅ | |
| privdata_len check → goto error | error (goto) | YES (qp_get) | YES (qp_put + final cep_put) | ✅ | |
| modify_qp fail → goto error | error (goto) | YES (qp_get, cep_get, add_ref) | YES (error label puts all) | ✅ | |
| send_mpareqrep fail → goto error | error (goto) | YES (qp_get, cep_get, add_ref) | YES (error label puts all) | ✅ | |
| upcall fail → goto error | error (goto) | YES (qp_get, cep_get, add_ref) | YES (error label puts all) | ✅ | |
| success → return 0 | success (return) | YES (qp_get, cep_get, add_ref) | NO (references kept for connection lifetime) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`erdma_accept` misses `erdma_cep_put(cep)` on the `if (!qp) return -ENOENT;` path, leaking the original cep reference that is properly released on all other error paths.
```
