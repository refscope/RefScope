# REAL BUG: fs/gfs2/ops_fstype.c:257 gfs2_glock_nq_init()

**Confidence**: LOW | **Counter**: `$->gh_owner_pid->count.refs.counter`

## Reasoning

Without the source for those callees, the error path exhibits a suspicious double-put pattern. Given the contract says `gfs2_holder_uninit` is a put-wrapper, and the warning pinpoints that call, I must assume there is a path where the PID reference is not properly held before the put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L255 (error ≠ 0) | error return | ❓ | YES (gfs2_holder_uninit) | ❓ | `__gfs2_holder_init` might not always get the PID ref, or `gfs2_glock_nq` might already release it before returning error → excess put. |
| L255 (error == 0) | success return | ❓ | NO | ❓ | The warning is about excess put, not leak. This path is irrelevant. |

[NEED_SOURCE] __gfs2_holder_init
[NEED_SOURCE] gfs2_glock_nq

The `gfs2_holder_uninit` contract states it unconditionally calls `put_pid` on the holder’s PID reference. For the error path in `gfs2_glock_nq_init()`, `__gfs2_holder_init` is called first (which should initialize the holder and, typically, acquire the PID reference). Then `gfs2_glock_nq()` is called; if it fails, `gfs2_holder_uninit` is invoked. An “excess put” warning at that line means the PID reference was already decremented to zero or had an imbalance. This can happen if:

1. `__gfs2_holder_init` does **not** always acquire a PID reference (e.g., only under certain states), and the error path triggers `put_pid` on a non-referenced PID.
2. `gfs2_glock_nq` itself, on failure, already calls `gfs2_holder_uninit` (or `put_pid`) before returning, leading to a double put.

Without the source for those callees, the error path exhibits a suspicious double-put pattern. Given the contract says `gfs2_holder_uninit` is a put-wrapper, and the warning pinpoints that call, I must assume there is a path where the PID reference is not properly held before the put.

VERDICT: REAL_BUG
CONFIDENCE: LOW
Likely double-put on `gh_owner_pid` in `gfs2_glock_nq_init` error path due to missing get or early release in `gfs2_glock_nq`. Source of `__gfs2_holder_init` and `gfs2_glock_nq` needed to confirm.
```
