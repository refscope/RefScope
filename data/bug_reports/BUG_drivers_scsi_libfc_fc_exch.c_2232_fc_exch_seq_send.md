# REAL BUG: drivers/scsi/libfc/fc_exch.c:2232 fc_exch_seq_send()

**Confidence**: MEDIUM | **Counter**: `$->ex_refcnt.counter`

## Reasoning

n is wrong and the delete call is superfluous (or the function should not call delete when done_locked already released the exchange).

[NEED_SOURCE] fc_exch_done_locked  
[NEED_SOURCE] fc_exch_delete

## Full Response

```
```
| Line | Return Type           | GET Done? (fc_exch_alloc) | PUT Done? (by done/delete) | Balanced? | Notes |
|------|-----------------------|---------------------------|----------------------------|-----------|-------|
| ~2183 | alloc NULL → return NULL | NO                        | N/A                        | ✅        | no exchange created |
| ~2217 | success → return sp     | YES                       | NO (ref given to caller)   | ✅        | caller owns ref, eventual put expected |
| ~2228 (rc==0) | error → rc=0 → fc_exch_delete(ep) → return NULL | YES | YES (done_locked + delete) | ❌ **EXCESS PUT** | `fc_exch_done_locked` likely already released the reference (perhaps freeing the exchange), then `fc_exch_delete` does another put → underflow |
| ~2228 (rc!=0) | error → rc!=0 → no delete → return NULL | YES | ? (depends on done_locked) | ?         | if done_locked doesn't put, ref might leak (but rc!=0 suggests still in use, maybe timer holds ref) |

**Analysis**  
The warning at line 2232 (`fc_exch_delete(ep)`) reports an excess put on `ex_refcnt.counter`. The error path calls `fc_exch_done_locked(ep)` and then, only when `rc` is 0, calls `fc_exch_delete(ep)`. In typical FC exchange management, `fc_exch_done_locked` already performs the final reference drop and may internally call the delete/free if the counter reaches zero. If it already does so, the subsequent `fc_exch_delete` would be an extra put, exactly matching the underflow warning. Without the exact contract or callee source for `fc_exch_done_locked` and `fc_exch_delete`, the most likely explanation is that the condition is wrong and the delete call is superfluous (or the function should not call delete when done_locked already released the exchange).

[NEED_SOURCE] fc_exch_done_locked  
[NEED_SOURCE] fc_exch_delete

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`fc_exch_done_locked(ep)` likely already consumes the initial reference, so the extra `fc_exch_delete(ep)` when rc==0 causes an excess put on the ex_refcnt.
```
```
