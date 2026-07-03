# REAL BUG: drivers/md/raid5.c:5298 handle_stripe()

**Confidence**: HIGH | **Counter**: `$->r5c_cached_partial_stripes.counter`

## Reasoning

| L5280 | `goto finish` (expansion) | depends | **YES** | ❌ if GET not done | same |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4918 | early return (`clear_batch_ready`) | NO (before any get) | NO (before any put) | ✅ | no ref opertions |
| L4924 | early return (STRIPE_ACTIVE) | NO | NO | ✅ | |
| L4960 | `goto finish` (LOG_TRAPPED) | NO | NO | ✅ | jumps to finish label, which is after `r5c_finish_stripe_write_out` but the goto itself skips that call |
| L4965 | `goto finish` (handle_bad_blocks) | NO | NO | ✅ | same |
| L4970 | `goto finish` (blocked_rdev) | NO | NO | ✅ | same |
| L5149 → normal flow (writeback block skipped due to `sh->reconstruct_state` / `sh->check_state` / `sh->log_io`) | fall‑through to finish | **NO** (writeback block not entered, `r5c_try_caching_write` never called) | **YES** (`r5c_finish_stripe_write_out` already executed unconditionally at L5149) | ❌ **EXCESS PUT** | counter decremented without prior increment → refcount underflow |
| L5149 → non‑writeback mode path (`!r5c_is_writeback`) | fall‑through | **NO** (no `r5c_try_caching_write`) | **YES** | ❌ | same |
| L5149 → writeback mode, `s.to_write == false` | fall‑through | **NO** | **YES** | ❌ | same |
| L5149 → writeback mode, `s.to_write`, `r5c_try_caching_write` returns `-EAGAIN` (failure) | fall‑through or `goto finish` L5192 | **NO** (get failed, no increment) | **YES** | ❌ | |
| L5149 → writeback mode, `r5c_try_caching_write` succeeds | fall‑through | **YES** | **YES** | ✅ | only balanced path among the non‑early‑return paths |
| L5192 | `goto finish` (handle_stripe_dirtying returns `-EAGAIN`) | depends (often NO) | **YES** | ❌ if GET not done | PUT already executed at L5149 |
| L5280 | `goto finish` (expansion) | depends | **YES** | ❌ if GET not done | same |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`r5c_finish_stripe_write_out` decrements the `r5c_cached_partial_stripes` counter unconditionally at L5149, but the matching `r5c_try_caching_write` (which increments) is only called under specific writeback conditions. Multiple paths (e.g., when `sh->reconstruct_state` or `sh->check_state` or `sh->log_io` are true, or non‑writeback mode) call the PUT without a prior GET, causing a refcount excess put / underflow on that global counter.
```
