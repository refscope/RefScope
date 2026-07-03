# REAL BUG: drivers/scsi/libfc/fc_fcp.c:1684 fc_fcp_rec_error()

**Confidence**: HIGH | **Counter**: `$->ref_cnt.refs.counter`

## Reasoning

- The warning explicitly flags line 1684 as “refcount excess put”, consistent with this pattern.

## Full Response

```
| Line | Return Type | GET Done? (lock_pkt) | PUT Done? (release + unlock_pkt) | Balanced? | Notes |
|------|-------------|----------------------|---------------------------------|-----------|-------|
| 1650 → goto out → 1684 (put) | void (implicit return) | NO (conditional get fails) | YES (fc_fcp_pkt_release only) | ❌ Excess PUT | lock_pkt returned non-zero → no get. The subsequent put at out drops the REC hold, but the REC hold may already be released if the packet is in COMPL state. Warning indicates refcount underflow. |
| 1650 → success → switch → unlock_pkt → out → 1684 (put) | void (implicit return) | YES (get from lock_pkt) | YES (unlock_pkt put + fc_fcp_pkt_release put) | ✅ Balanced | Two gets (lock_pkt + pre‑existing REC hold) and two puts. |

**Application of FP checklist**:
- No IS_ERR/NULL guard that would invalidate the implicit REC hold.
- No ownership transfer or deferred release.
- The `goto out` after a failed `fc_fcp_lock_pkt` leads directly to a put, but no get occurred on that path. The pre‑existing REC hold may have been dropped if the packet is already complete, causing an excess put.
- The warning explicitly flags line 1684 as “refcount excess put”, consistent with this pattern.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`fc_fcp_lock_pkt` is a conditional get; failing it bypasses any internal get, yet the `out` label always calls `fc_fcp_pkt_release`. If the REC hold has already been released (e.g., due to FC_SRB_COMPL), this put is superfluous and underflows the refcount, exactly as the excess‑put warning reports.
```
