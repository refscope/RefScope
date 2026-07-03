# REAL BUG: drivers/scsi/qedf/qedf_els.c:992 qedf_rec_compl()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

- goto out between GET and PUT? Not relevant.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L844 | goto out_free (orig_io_req is NULL) | NO (no get) | NO (skips out_put) | ✅ | No reference held |
| L857 | goto out_put (rec_req event TMO) | NO (no get before) | YES (out_put kref_put) | ✅ | Releases initial reference |
| L880 | goto out_put (fc_frame_alloc fails) | NO (no get) | YES (out_put) | ✅ | Releases initial reference |
| L~910 (LS_RJT, rjt present, condition matches → qedf_requeue_io_req called, fall through to out_free_frame→out_put) | normal exit (fall through) | NO (no get) | YES (qedf_requeue_io_req does kref_put(s) + out_put kref_put) → PUT > GET | ❌ EXCESS PUT | **WARNING**: extra put after requeue drops ref underflow |
| L~910 (LS_RJT, condition not matched, no requeue, fall through) | normal exit | NO | YES (out_put only) | ✅ | |
| L~975 (LS_ACC, srr_needed → qedf_send_srr gets, fall through) | normal exit | YES (unconditional get) | YES (out_put only) | ❌ LEAK (GET > PUT) | Not “excess put”, but under-put |
| L~975 (LS_ACC, !srr_needed → qedf_initiate_seq_cleanup gets, fall through) | normal exit | YES (unconditional get) | YES (out_put only) | ❌ LEAK | Same – leak but not “excess put” |

**Pre‑verdict checklist**:
- “Held for device lifetime”? Not applicable.
- Ownership transfer? Comment indicates `qedf_requeue_io_req` re‑issues the request and should consume the reference; but the code falls through to the unconditional `kref_put` at `out_put`, resulting in an extra put → real bug.
- Unconditional GET? Not in the affected path.
- goto out between GET and PUT? Not relevant.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`qedf_requeue_io_req` releases the reference (contract shows `kref_put`) in the ELS_RJT/CMD LOST path, yet the function always performs an additional `kref_put` at `out_put`, causing a refcount underflow at line 992.
```
