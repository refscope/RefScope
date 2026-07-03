# REAL BUG: drivers/infiniband/hw/erdma/erdma_cm.c:1373 erdma_create_listen()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L1346 | goto error  | YES (alloc+assoc) | NO | ❌ LEAK | provider_data alloc fail; same |

## Full Response

```
[NEED_SOURCE] erdma_socket_disassoc

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1306 | error       | NO (no cep alloc) | N/A  | ✅ | early addr family check |
| L1310 | error       | NO (before cep) | N/A  | ✅ | sock_create failed |
| L1321 | goto error  | NO (cep=NULL) | N/A  | ✅ | bind failed, cep not allocated |
| L1326 | goto error  | NO (alloc failed) | N/A  | ✅ | erdma_cep_alloc failed |
| L1332 | goto error  | YES (alloc+assoc) | NO (one put only, assoc ref leak) | ❌ LEAK | erdma_cm_alloc_work fail; error path does erdma_cep_put once, but ref=2 |
| L1336 | goto error  | YES (alloc+assoc) | NO | ❌ LEAK | listen fail; same |
| L1346 | goto error  | YES (alloc+assoc) | NO | ❌ LEAK | provider_data alloc fail; same |
| L1354 | success     | YES (alloc+assoc) | N/A (transferred) | ✅ | cep added to list, ownership moved; ref held by list/socket |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
erdma_cep_socket_assoc unconditionally acquires a reference (ref →2). Error paths after that (L1332, L1336, L1346) jump to the error label, which only calls erdma_cep_put once (L1369), leaving the assoc reference leaked. The preceding `cep->sock = NULL` (L1364) likely prevents erdma_socket_disassoc from releasing that ref even if it normally would.
```
