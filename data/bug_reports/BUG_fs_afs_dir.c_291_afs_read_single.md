# REAL BUG: fs/afs/dir.c:291 afs_read_single()

**Confidence**: MEDIUM | **Counter**: `$->n_active.counter`

## Reasoning

| L290 | success (return ret) | YES (fscache_use_cookie at L287 increments n_active.counter) | NO (fscache_unuse_cookie at L289 does not decrement n_active.counter) | ❌ LEAK | Counter n_active.counter is never released. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L290 | success (return ret) | YES (fscache_use_cookie at L287 increments n_active.counter) | NO (fscache_unuse_cookie at L289 does not decrement n_active.counter) | ❌ LEAK | Counter n_active.counter is never released. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
fscache_use_cookie bumps n_active.counter, but the function never calls a matching decrement for that counter; fscache_unuse_cookie likely handles a different usage counter, leaving the refcount leak.
```
