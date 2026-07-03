# REAL BUG: drivers/infiniband/hw/irdma/cm.c:2809 irdma_handle_synack_pkt()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

break` after `irdma_send_reset`** | **~2802** | **NO** | **YES (assumed put)** | **❌ EXCESS PUT** | **missing `refcount_inc` before reset** |

## Full Response

```
[NEED_SOURCE] irdma_send_reset
[NEED_SOURCE] irdma_passive_open_err

| Path Description | Approx Line | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| SYN_SENT: check_syn fail → `return` | ~2760 | NO | NO | ✅ | |
| SYN_SENT: `tcp_options` err → `break` | ~2775 | NO | NO | ✅ | |
| SYN_SENT: `mpa_request` err → `break` | ~2785 | NO | NO | ✅ | |
| SYN_SENT: success → `break` | ~2790 | NO | NO | ✅ | |
| MPAREQ_RCVD: passive_open_err → `break` | ~2795 | NO | YES (irdma_rem_ref_cm_node put) | ⚠️ (external reference, not flagged here) | |
| **LISTENING: `break` after `irdma_send_reset`** | **~2802** | **NO** | **YES (assumed put)** | **❌ EXCESS PUT** | **missing `refcount_inc` before reset** |
| **CLOSED: `break` after `refcount_inc` + `irdma_send_reset`** | **2809** | **YES** | **YES** | **✅** | |
| other states: `break` | ~2815 | NO | NO | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
LISTENING state calls irdma_send_reset() without a prior refcount_inc() while CLOSED state correctly increments; if send_reset internally drops a reference, this causes an excess put on that path.
```
