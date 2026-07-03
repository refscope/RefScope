# REAL BUG: fs/gfs2/file.c:1542 do_flock()

**Confidence**: HIGH | **Counter**: `$->gh_owner_pid->count.refs.counter`

## Reasoning

| L1527‑1528, error (locks_lock_file_wait fails) | **error** | **YES** | **NO** | **❌ LEAK** | __flock_holder_uninit is not called; pid ref leaked |

## Full Response

```
| Line(s) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|---------|-------------|-----------|-----------|-----------|-------|
| L1500 (goto out) | early return (state match) | NO (holder already initialized, no new get) | N/A | ✅ | existing ref retained |
| L1510 (goto out) | error (gfs2_glock_get fails) | NO | N/A | ✅ | holder not initialized yet |
| L1523‑1525 (error from gfs2_glock_nq) | error | YES (from gfs2_holder_reinit / gfs2_holder_init) | YES (__flock_holder_uninit) | ✅ | proper cleanup |
| L1527‑1528, success (locks_lock_file_wait returns 0) | success (error = 0) | YES | NO | ✅ | holder intentionally held for successful lock |
| L1527‑1528, error (locks_lock_file_wait fails) | **error** | **YES** | **NO** | **❌ LEAK** | __flock_holder_uninit is not called; pid ref leaked |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`do_flock()` fails to call `__flock_holder_uninit()` when `locks_lock_file_wait()` returns an error after a successful `gfs2_glock_nq()`, leaking the pid reference obtained by `gfs2_holder_init`/`gfs2_holder_reinit`.
```
