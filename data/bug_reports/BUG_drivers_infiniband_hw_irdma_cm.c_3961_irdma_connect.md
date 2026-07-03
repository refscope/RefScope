# REAL BUG: drivers/infiniband/hw/irdma/cm.c:3961 irdma_connect()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L3910 | success (return 0) | YES | NO (intentional) | ✅ | node kept alive for hash lifetime |

## Full Response

```
| Line | Return Type | GET Done? (qhash) | PUT Done? (via err) | Balanced? | Notes |
|------|-------------|-------------------|---------------------|-----------|-------|
| L3825 | error (ibqp) | NO (before node) | N/A | ✅ | no cm_node ref |
| L3827 | error (iwqp) | NO (before node) | N/A | ✅ | no cm_node ref |
| L3829 | error (iwdev) | NO (before node) | N/A | ✅ | no cm_node ref |
| L3835 | error (port) | NO (before node) | N/A | ✅ | no cm_node ref |
| L3845 | error (MTU4) | NO (before node) | N/A | ✅ | no cm_node ref |
| L3851 | error (MTU6) | NO (before node) | N/A | ✅ | no cm_node ref |
| L3870 | error (ws_add) | NO (before node) | N/A | ✅ | no cm_node ref |
| L3880 | error (create fail) | NO (node NULL) | N/A | ✅ | create failed, no ref |
| L3885 | goto err (AH fail) | NO (before qhash) | YES (one put) | ✅ | initial ref released |
| L3890 | goto err (qhash fail) | NO (qhash failed, no extra ref) | YES (one put) | ✅ | initial ref released |
| L3895 | goto err (apbvt fail) | YES (qhash succeeded) | YES (one put) | ❌ LEAK | two refs held (1 initial + 1 qhash), only one put |
| L3905 | goto err (send_syn fail) | YES (qhash succeeded) | YES (one put) | ❌ LEAK | same, two refs held, one put |
| L3910 | success (return 0) | YES | NO (intentional) | ✅ | node kept alive for hash lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`irdma_manage_qhash` acquires an extra ref on `cm_node` on success; two error paths after that point (apbvt fail, send_syn fail) jump to `err` which releases only the initial ref via `irdma_rem_ref_cm_node`, leaking the qhash reference.
```
