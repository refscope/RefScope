# REAL BUG: kernel/events/core.c:5163 find_get_context()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L? (success after alloc) | success (ctx returned) | YES (alloc + get_ctx) | NO (caller put) | ✅ | stored in task->perf_event_ctxp, caller responsible |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L? (perf_allow_cpu err) | error (ERR_PTR) | NO (before get) | N/A | ✅ | |
| L? (!task success) | success (ctx returned) | YES (get_ctx) | NO (caller put) | ✅ | normal acquisition |
| L? (if(ctx) block) | success (ctx returned) | YES (from perf_lock_task_context) | NO (caller put) | ✅ | locked context success path |
| L? (alloc_perf_context NULL) | error (goto errout) | NO (alloc failed) | N/A | ✅ | |
| L? (err == -ESRCH) | error (goto errout after put_ctx) | YES (alloc + get_ctx) | YES (put_ctx once) | ❌ LEAK | alloc refcount 1, get_ctx inc to 2, single put_ctx dec to 1, context never freed |
| L? (err == -EAGAIN) | retry (goto retry after put_ctx) | YES (alloc + get_ctx) | YES (put_ctx once) | ❌ LEAK | same refcount mismatch, pointer overwritten on retry |
| L? (success after alloc) | success (ctx returned) | YES (alloc + get_ctx) | NO (caller put) | ✅ | stored in task->perf_event_ctxp, caller responsible |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`alloc_perf_context` returns a context with refcount 1 (implicit from init). The `else` branch calls `get_ctx(ctx)` raising refcount to 2. On error (-ESRCH or -EAGAIN) only a single `put_ctx(ctx)` is called, leaving the allocation reference undropped, leaking the context.
```
