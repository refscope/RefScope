# REAL BUG: fs/dlm/lock.c:5798 dlm_user_request()

**Confidence**: LOW | **Counter**: `$->lkb_ref.refcount.refs.counter`

## Reasoning

| Success (0 / -EINPROGRESS) → fall through `out_put` (do_put=false) | success return | 2 (create_lkb + hold_lkb) | 0 | ❓ (net +2) | Intended: list holds 1 ref, request holds 1 ref |

## Full Response

```
| Path | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| create_lkb error → `out` | error return | NO (lkb not created) | N/A | ✅ | No ref acquired |
| lvbptr alloc fail → `goto out_put` | error return | 1 (from create_lkb) | 1 (`__put_lkb`, do_put=true) | ✅ | drop initial ref |
| set_lock_args error → `goto out_put` | error return | 1 | 1 | ✅ | drop initial ref |
| request_lock error (-EAGAIN or other default) → `goto out_put` | error return | 1 | 1 | ✅ | drop initial ref |
| Success (0 / -EINPROGRESS) → fall through `out_put` (do_put=false) | success return | 2 (create_lkb + hold_lkb) | 0 | ❓ (net +2) | Intended: list holds 1 ref, request holds 1 ref |

VERDICT: REAL_BUG
CONFIDENCE: LOW
The `__put_lkb` at the `out_put` label (line 5798) is reached on error paths where `request_lock` has already returned an error. If `request_lock` itself internally holds a reference and drops it on failure, this `__put_lkb` becomes an excess put (double-put). On the other hand, if `create_lkb` does not set the refcount to 1 (e.g., starts at 0), the initial put is already excess. Either way, the warning indicates an imbalance. [NEED_SOURCE] request_lock, [NEED_SOURCE] create_lkb, [NEED_SOURCE] __put_lkb are required to confirm the exact cause.
```
