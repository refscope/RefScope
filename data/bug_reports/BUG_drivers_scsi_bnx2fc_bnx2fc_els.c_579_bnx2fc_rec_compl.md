# REAL BUG: drivers/scsi/bnx2fc/bnx2fc_els.c:579 bnx2fc_rec_compl()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| ACC: e_stat & ESB_ST_SEQ_INIT | goto free_frame | No | Balanced | |

## Full Response

```
```
| Path | Line/dest | Prior PUT (before L579)? | Excess at L579? | Notes |
|------|-----------|---------------------------|-----------------|-------|
| TIMEOUT: bnx2fc_send_rec(orig_io_req) succeeds | L404 goto rec_compl_done | UNCERTAIN: bnx2fc_send_rec contracts show kref_put | Possible | If send_rec decrements ref, L579 is extra put |
| TIMEOUT: send_rec fails → abts on orig_io_req → cleanup on failure | L411 goto rec_compl_done | **YES** (bnx2fc_initiate_cleanup called) | **Yes** | cleanup called before L579 → double put |
| TIMEOUT: send_rec fails → abts succeeds (no cleanup) | L411 goto rec_compl_done | UNCERTAIN (abts unknown) | Uncertain | abts may not release ref |
| IO_COMPL flag set | L396 goto rec_compl_done | No | Balanced | Normal path |
| ISSUE_ABTS flag set | L400 goto rec_compl_done | No | Balanced | |
| kzalloc fail | L417 goto rec_compl_done | No | Balanced | |
| fc_frame_alloc fail | L423 goto free_buf → rec_compl_done | No | Balanced | |
| RJT: new_io_req alloc fails → abort_io → abts + cleanup on failure | L474→abort_io→free_frame→rec_compl_done | **YES** (cleanup if abts fails) | **Yes** | |
| RJT: new_io_req ok, cleanup called, post_io_req fails → abort_io → abts+cleanup | same | **YES** (cleanup already called once, potentially again) | **Yes** | |
| RJT: new_io_req ok, post_io_req success → free_frame | L489 free_frame | **YES** (cleanup at L469) | **Yes** | cleanup before L579 |
| ACC: seq_cleanup fails, abort_io = true → abts + cleanup | abort_io block → free_frame | **YES** (cleanup if abts fails) | **Yes** | |
| ACC: send_srr(orig_io_req) called | L540-544 → free_frame | UNCERTAIN (bnx2fc_send_srr contract shows kref_put) | Possible | |
| ACC: e_stat & ESB_ST_SEQ_INIT | goto free_frame | No | Balanced | |
| ACC: send_seq_clnp true, abort_io false, no send_srr | falls through free_frame | No | Balanced | |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
Multiple paths call `bnx2fc_initiate_cleanup(orig_io_req)` or functions with `kref_put` semantics before the final `kref_put` at L579, causing an excess put. Exact callee internals (`bnx2fc_initiate_cleanup`, `bnx2fc_initiate_abts`) not provided; confidence medium pending source review via [NEED_SOURCE] bnx2fc_initiate_cleanup and [NEED_SOURCE] bnx2fc_initiate_abts.
```
```
