# REAL BUG: fs/gfs2/quota.c:257 gfs2_glock_nq_init()

**Confidence**: LOW | **Counter**: `$->gh_owner_pid->count.refs.counter`

## Reasoning

However, based on the live refcount tracker evidence, the error path is releasing a reference that was never acquired.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L259 (return error; error == 0) | success | YES (assuming __gfs2_holder_init takes PID ref) | NO | ✅ (holder kept, put elsewhere) | success path: holder alive |
| L256 (goto err via if(error)) | error return after uninit | **NO** (deduced from excess‑put warning) | YES (gfs2_holder_uninit) | ❌ EXCESS PUT | `gfs2_holder_uninit` calls `put_pid` but pid ref not taken → underflow |

**Notes:**  
The warning explicitly identifies a `refcount excess put` on `gh_owner_pid->count.refs` inside the error path. This indicates that `__gfs2_holder_init` **did not** take a PID reference in this context, making the unconditional `gfs2_holder_uninit` call an over-release. To confirm the exact GET contract I need:  
[NEED_SOURCE] __gfs2_holder_init  
However, based on the live refcount tracker evidence, the error path is releasing a reference that was never acquired.

VERDICT: REAL_BUG  
CONFIDENCE: LOW  
`gfs2_holder_uninit` on error releases a PID ref that was never taken by `__gfs2_holder_init`, causing an `excess put`.
```
