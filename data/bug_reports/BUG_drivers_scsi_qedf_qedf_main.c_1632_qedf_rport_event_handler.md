# REAL BUG: drivers/scsi/qedf/qedf_main.c:1632 qedf_rport_event_handler()

**Confidence**: HIGH | **Counter**: `qedf->num_offloads.counter`

## Reasoning

d) | NO | YES | ❌ EXCESS | Flag SESSION_READY never cleared → second LOGO does extra atomic_dec |
| case LOGO/FAILED/STOP, session ready bit not set → break (L1632 skipped) | break | NO | NO | N/A | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| case READY, rport NULL → break (L1475) | break | NO | NO | N/A | no get/put |
| case READY, num_offloads >= MAX → return (L1483) | return | NO | NO | N/A | |
| case READY, session already ready → return (L1491) | return | NO | NO | N/A | |
| case READY, dir server → break (L1498) | break | NO | NO | N/A | |
| case READY, spp_type != FCP → break (L1505) | break | NO | NO | N/A | |
| case READY, !FCP target role → break (L1512) | break | NO | NO | N/A | |
| case READY, qedf_alloc_sq fails → break (after L1520) | break | NO | NO | N/A | |
| case READY, qedf_offload_connection fails → break (after L1536) | break | NO | NO | N/A | |
| case READY, success → break (after L1547) | break | YES (atomic_inc) | NO | No (deferred to LOGO) | intended cross‑event balance |
| case LOGO/FAILED/STOP, dir server → break (L1557) | break | NO | NO | N/A | |
| case LOGO/FAILED/STOP, spp_type != FCP → break (L1564) | break | NO | NO | N/A | |
| case LOGO/FAILED/STOP, !FCP target → break (L1571) | break | NO | NO | N/A | |
| case LOGO/FAILED/STOP, !rport → break (L1578) | break | NO | NO | N/A | |
| case LOGO/FAILED/STOP, session ready bit set → break (L1632) | break (atomic_dec executed) | NO | YES | ❌ EXCESS | Flag SESSION_READY never cleared → second LOGO does extra atomic_dec |
| case LOGO/FAILED/STOP, session ready bit not set → break (L1632 skipped) | break | NO | NO | N/A | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`atomic_dec(&qedf->num_offloads)` at L1632 is guarded by `test_bit(QEDF_RPORT_SESSION_READY)`, but that bit is never cleared after the session is torn down, allowing repeated `atomic_dec` on subsequent LOGO/FAILED/STOP events — a true excess put and refcount underflow.
```
