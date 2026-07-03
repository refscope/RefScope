# REAL BUG: fs/gfs2/aops.c:257 gfs2_glock_nq_init()

**Confidence**: LOW | **Counter**: `$->gh_owner_pid->count.refs.counter`

## Reasoning

| `gfs2_glock_nq` returns 0, `return 0` | success | YES (assuming `__gfs2_holder_init` gets ref) | NO | ✅ (no put → no excess) | Ref held for later release by holder dequeue; not relevant to excess‑put warning. |

## Full Response

```
| Path | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| `gfs2_glock_nq` returns error, then `gfs2_holder_uninit(gh)`, then `return error` | error | **unknown** (depends on whether `__gfs2_holder_init` always takes a PID ref) | YES (`gfs2_holder_uninit`) | ? | If `__gfs2_holder_init` unconditionally gets PID ref, this path is balanced; if `gfs2_glock_nq` also calls `gfs2_holder_uninit` (or `put_pid`) on failure, this would be an excess put (double uninit). |
| `gfs2_glock_nq` returns 0, `return 0` | success | YES (assuming `__gfs2_holder_init` gets ref) | NO | ✅ (no put → no excess) | Ref held for later release by holder dequeue; not relevant to excess‑put warning. |

[NEED_SOURCE] __gfs2_holder_init
[NEED_SOURCE] gfs2_glock_nq

VERDICT: REAL_BUG
CONFIDENCE: LOW

Possible double-release: `gfs2_glock_nq` may internally clean up the holder on failure (e.g., calling `gfs2_holder_uninit` or dropping the PID ref), and the caller’s explicit `gfs2_holder_uninit(gh)` then causes an excess put on `gh_owner_pid`. Without the callees’ source, the exact root is unconfirmed.
```
