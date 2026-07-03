# REAL BUG: drivers/infiniband/hw/erdma/erdma_cm.c:892 erdma_cm_work_handler()

**Confidence**: MEDIUM | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L892 | MPATIMEOUT — AWAIT_MPAREQ | None | explicit `erdma_cep_put(cep)`, release_cep block (cm_id maybe), final | Balanced (work+listen) | |

## Full Response

```
| Line | Path Description | GET Done? (on cep) | PUTs before final | Balanced? | Notes |
|------|-------------------|---------------------|--------------------|-----------|-------|
| L892 | CONNECTED — erdma_newconn_connected success, no release_cep | None (except maybe cancel_mpatimer get?) | cancel_mpatimer(cep) x1 (if puts), no other | Possibly balanced (work ref) | cancel_mpatimer may put; otherwise final aligns with work ref. |
| L892 | CONNECTED — error, release_cep=1 | `erdma_newconn_connected` returns error | cancel_mpatimer(cep) x2 (first in case, then in release_cep block), cm_id put if cm_id | Might be balanced if cancel_mpatimer does not double-put and cm_id reference exists. | Double cancel_mpatimer could double-put if not guarded. |
| L892 | CONNECTTIMEOUT — release_cep=1 | None | release_cep block: cancel_mpatimer(cep) (if puts), cm_id put if cm_id | Likely balanced (work + cm_id) | |
| L892 | ACCEPT — erdma_accept_newconn(cep) | erdma_accept_newconn may get (conditional) | None explicit; final put | Balanced if work ref is separate | \( \text{erdma\_accept\_newconn} \) may transfer ownership; still work ref needs dropping. |
| L892 | READ_MPAHDR — listen_cep non-NULL, ret 0 success | erdma_proc_mpareq may get | No cep put, only listen_cep put | Balanced (work ref) | |
| L892 | READ_MPAHDR — listen_cep non-NULL, ret -EAGAIN | None (maybe none) | None on cep | Balanced | |
| L892 | READ_MPAHDR — listen_cep non-NULL, ret error (≠ -EAGAIN) | erdma_proc_mpareq may get/put internally | 1 explicit `erdma_cep_put(cep)`, possibly cm_id put in release_cep, final put | ⚠️ Potential excess put if erdma_proc_mpareq also puts internally, causing refcount underflow before final put. | Handler does unconditional put on error; if callee also puts, double-put. Release_cep may add another put. |
| L892 | READ_MPAHDR — AWAIT_MPAREP, ret error | erdma_proc_mpareply may put? | release_cep block (cm_id), final | Balanced if cm_id held | |
| L892 | CLOSE_LLP — release_cep=1 | None | release_cep block (cancel_mpatimer, cm_id put), final | Balanced (work + cm_id) | |
| L892 | PEER_CLOSE — AWAIT_MPAREQ branch | None | explicit `erdma_cep_put(cep)`, release_cep block (cm_id maybe), final | Balanced (work+listen) if cm_id NULL | |
| L892 | PEER_CLOSE — other states | None | release_cep block (cm_id), final | Balanced (work+cm_id) | |
| L892 | MPATIMEOUT — AWAIT_MPAREP | None | release_cep block (cm_id), final | Balanced | |
| L892 | MPATIMEOUT — AWAIT_MPAREQ | None | explicit `erdma_cep_put(cep)`, release_cep block (cm_id maybe), final | Balanced (work+listen) | |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The READ_MPAHDR error path calls `erdma_cep_put(cep)` unconditionally when `erdma_proc_mpareq(cep)` fails, and then sets `release_cep` which may lead to an additional put for the cm_id. Since the contract states `erdma_proc_mpareq` can itself call `erdma_cep_put`, the explicit put in the handler can double-decrement the refcount, and the final put at line 892 wo
```
