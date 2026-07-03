# REAL BUG: fs/lockd/svcproc.c:364 nlmsvc_callback()

**Confidence**: HIGH | **Counter**: `$->a_count.refs.counter`

## Reasoning

| L362 (async_reply < 0) | error | YES | NO | ❌ LEAK | no release before return |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L343 (host==NULL) | error | NO (before alloc) | N/A | ✅ | |
| L350 (call==NULL) | error | NO (alloc failed) | N/A | ✅ | |
| L355 (stat != 0) | error | YES | YES | ✅ | explicit nlmsvc_release_call |
| L362 (async_reply < 0) | error | YES | NO | ❌ LEAK | no release before return |
| L363 (async_reply success) | success | YES | NO (transferred) | ✅ | ownership passed to async callback |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
nlm_alloc_call always incs, async_reply failure at L362 returns without nlmsvc_release_call, leaking the call reference.
```
