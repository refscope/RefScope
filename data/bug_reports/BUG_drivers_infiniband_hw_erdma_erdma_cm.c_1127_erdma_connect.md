# REAL BUG: drivers/infiniband/hw/erdma/erdma_cm.c:1127 erdma_connect()

**Confidence**: MEDIUM | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

rdma_socket_disassoc` is not annotated with a cep‑put in the contracts; if it does internally `erdma_cep_put`, the LEAK markings become balanced. Without evidence of such a put, the error‑dissociation paths are missing a reference release from `erdma_cep_socket_assoc`, leaving a dangling refcount.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1023 | error (return -EINVAL) | NO (before any get) | N/A | ✅ | |
| L1027-1028 | error (return -EINVAL) | NO | N/A | ✅ | |
| L1031 | error (return -EAFNOSUPPORT) | NO | N/A | ✅ | |
| L1036 | error (return -ENOENT) | NO | N/A | ✅ | |
| L1042 | goto error_put_qp (sock_create fail) | NO (cep alloc not yet attempted) | N/A | ✅ | qp_get was done, qp_put will balance qp refs |
| L1046 | goto error_release_sock (cep alloc fail) | NO (no cep object) | N/A | ✅ | |
| L1053 | erdma_cep_get(qp assoc) → ref now 2 | YES (cep alloc + qp_assoc get) | — | — | still in‑function |
| L1066 | goto error_release_cep (alloc_work fail) | YES (2) | YES (error_release_cep does two puts) | ✅ | refcount 2 → 0, no socket_assoc yet |
| L1077 | erdma_cep_socket_assoc → ref now 3 | YES (3) | — | — | |
| L1084 | goto error_disassoc (kmalloc fail) | YES (3) | NO (disassoc assumed NO put + two puts = 2) | ❌ LEAK | refcount 1 left after cleanup |
| L1094 | goto error_disassoc (kernel_bindconnect fail) | YES (3) | NO (disassoc assumed no put + 2 puts = 2) | ❌ LEAK | |
| L1097 | goto error_disassoc (queue_work CONNECTED fail) | YES (3 or 4, see work get) | NO (disassoc assumed no put + 2 puts) | ❌ LEAK | if queue_work holds its get on error → even higher leak |
| L1103 | goto error_disassoc (queue_work TIMEOUT fail) | YES (3 or 4) | NO (same) | ❌ LEAK | |
| L1115 | return 0 (success) | YES (3 or 4) | NO (held for connection lifetime) | ✅ (by design) | references expected to be released by upper layer / work callback |

**Key:** GET/PUT counts reflect only the cep kref. The function `erdma_socket_disassoc` is not annotated with a cep‑put in the contracts; if it does internally `erdma_cep_put`, the LEAK markings become balanced. Without evidence of such a put, the error‑dissociation paths are missing a reference release from `erdma_cep_socket_assoc`, leaving a dangling refcount.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
One-line reasoning: `erdma_cep_socket_assoc` unconditionally gets a cep reference (ref 3), but `error_disassoc` calls `erdma_socket_disassoc` which (assuming no implicit cep‑put) drops only the socket, not the cep ref; the subsequent two puts in `error_release_cep` leave refcount = 1, leaking the cep on all post‑socket‑assoc error paths.
```
