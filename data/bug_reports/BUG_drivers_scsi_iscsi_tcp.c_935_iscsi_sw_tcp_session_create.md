# REAL BUG: drivers/scsi/iscsi_tcp.c:935 iscsi_sw_tcp_session_create()

**Confidence**: HIGH | **Counter**: `$->shost_gendev.kobj.kref.refcount.refs.counter`

## Reasoning

**Note:** `iscsi_session_teardown` likely calls `scsi_host_put` as part of destroying the session, so combining it with `iscsi_host_free` on the `remove_session` path results in an extra release of the host’s kref.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L882 | error (ep) | NO (before alloc) | N/A | ✅ | |
| L892 | error (alloc fail) | NO (alloc failed) | N/A | ✅ | |
| L903 | goto free_host (rc<0) | YES (alloc succeeded) | YES (iscsi_host_free) | ✅ | |
| L906 | goto free_host (host_add fail) | YES | YES | ✅ | |
| L914 | goto remove_host (session_setup fail) | YES | YES (iscsi_host_free via fall‑through) | ✅ | host_add succeeded, but session_setup did not add extra ref |
| L917 | goto remove_session (pool_alloc fail) | YES (alloc) + YES (session_setup succeeded → extra ref on host) | YES (iscsi_session_teardown likely puts host) THEN YES (iscsi_host_free) → **excess put** | ❌ | session_teardown releases the session’s host reference; free_host releases again → double put |
| L922 | success (return cls_session) | YES (alloc) + YES (session_setup) | NO (ownership transferred) | ✅ | host ref held by session, released later |

**Note:** `iscsi_session_teardown` likely calls `scsi_host_put` as part of destroying the session, so combining it with `iscsi_host_free` on the `remove_session` path results in an extra release of the host’s kref.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
On the `remove_session` path (`iscsi_tcp_r2tpool_alloc` failure), `iscsi_session_teardown` already drops the host reference obtained by `iscsi_session_setup`, but the code then falls through to `iscsi_host_free` which decrements the host refcount again, causing a refcount underflow. The fix is to avoid calling `iscsi_host_free` after a successful `iscsi_session_setup` when `iscsi_session_teardown` will handle cleanup, or to restructure the labels so that `free_host` is not reached after `remove_session`.
```
