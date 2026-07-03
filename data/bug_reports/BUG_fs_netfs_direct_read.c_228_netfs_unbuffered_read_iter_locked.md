# REAL BUG: fs/netfs/direct_read.c:228 netfs_unbuffered_read_iter_locked()

**Confidence**: MEDIUM | **Counter**: `$->ref.refs.counter`

## Reasoning

Given the warning points to the line where this caller does the final PUT, and the report is “refcount excess put”, it is highly likely that `netfs_unbuffered_read` already brought the refcount to zero, making the caller’s PUT extra.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L157 | return 0 | NO (before alloc) | N/A | ✅ | early exit, no request allocated |
| L163 | return ret (<0) | NO (before alloc) | N/A | ✅ | kiocb_write_and_wait fail, no request |
| L176 | return PTR_ERR(rreq) | NO (alloc failed, IS_ERR guard) | N/A | ✅ | no valid rreq |
| L186 | goto error_put | YES (alloc succeeded) | YES (netfs_put_failed_request) | ✅ | explicit error cleanup |
| L209 | goto out (sync=false, ret<0) | YES | YES (netfs_put_request) | ⚠️ | if netfs_unbuffered_read already put, this is double-put |
| L214‑217 | fall through to out (sync=true, ret≥0) | YES | YES (netfs_put_request) | ⚠️ | same double-put risk if netfs_unbuffered_read already consumed the ref |
| L209 | goto out (any other ret<0) | YES | YES (netfs_put_request) | ⚠️ | ditto |

⚠️ The ambiguity arises because **netfs_unbuffered_read()** (called at line 203) is not shown. If that function internally calls `netfs_put_request()` before returning, then the subsequent `netfs_put_request()` at line 228 (out) becomes an excess put, exactly as smatch warns. The analysis must determine whether netfs_unbuffered_read already releases the reference. I request its source:

[NEED_SOURCE] netfs_unbuffered_read

Pending that source, the path table shows that, based solely on the visible function, every execution path has exactly one PUT for the one GET from `netfs_alloc_request`. The double‑put (excess‑put) can only be introduced by a hidden PUT inside `netfs_unbuffered_read`.

Given the warning points to the line where this caller does the final PUT, and the report is “refcount excess put”, it is highly likely that `netfs_unbuffered_read` already brought the refcount to zero, making the caller’s PUT extra.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
netfs_unbuffered_read likely already releases the request (puts reference) on error or completion; the caller’s netfs_put_request at line 228 then causes an excess put. Source of netfs_unbuffered_read needed for final confirmation.
```
