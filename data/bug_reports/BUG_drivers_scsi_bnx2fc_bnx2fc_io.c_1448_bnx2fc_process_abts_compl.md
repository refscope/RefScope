# REAL BUG: drivers/scsi/bnx2fc/bnx2fc_io.c:1448 bnx2fc_process_abts_compl()

**Confidence**: HIGH | **Counter**: `io_req->refcount.refcount.refs.counter`

## Reasoning

| **L1448** | **implicit return (wait_for_abts_comp false, goto from L1386)** | **NO** (timer_set skipped) | **YES (kref_put at L1448)** | **❌ EXCESS PUT** | **IO_CLEANUP already set → reference already released; this extra put causes refcount underflow.** |

## Full Response

```
| Line | Return Type                          | GET Done?                | PUT Done?                              | Balanced?     | Notes                                                                                                                                   |
|------|-------------------------------------|--------------------------|----------------------------------------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| L1370 | early return (ABTS_DONE set)       | NO (before any get)      | NO                                     | ✅            | Returns without ref operations; no leak.                                                                                                |
| L1430 | implicit return (wait_for_abts_comp true, normal path) | YES (timer_set at L1424) | NO                                     | ❌ LEAK       | timer reference obtained but not released; not the excess‑put warning.                                                                  |
| L1430 | implicit return (wait_for_abts_comp true, goto from L1386) | NO (timer_set skipped)   | NO                                     | ✅            | No gets, no puts; IO already cleaned up.                                                                                                |
| L1448 | implicit return (wait_for_abts_comp false, normal path) | YES (timer_set at L1424) | YES (kref_put at L1448, plus possible earlier cancel_delayed_work put) | ⚠️ potentially OK | Needs caller reference; not the warning.                                                                                               |
| **L1448** | **implicit return (wait_for_abts_comp false, goto from L1386)** | **NO** (timer_set skipped) | **YES (kref_put at L1448)** | **❌ EXCESS PUT** | **IO_CLEANUP already set → reference already released; this extra put causes refcount underflow.** |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
When `test_and_set_bit(BNX2FC_FLAG_IO_CLEANUP)` is true (line 1384) the code jumps to `io_compl`, skipping `bnx2fc_cmd_timer_set`. If `wait_for_abts_comp` is false, it reaches the `kref_put` at line 1448 without holding any reference, causing a refcount excess put on an already‑cleaned‑up request.
```
