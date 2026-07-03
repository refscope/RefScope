# REAL BUG: drivers/gpu/drm/i915/gt/intel_reset.c:1578 __igt_reset_evict_vma()

**Confidence**: HIGH | **Counter**: `$->usage.refs.counter`

## Reasoning

- No ownership transfer or deferred release pattern accounts for the missing put.

## Full Response

```
| Line | Return Type | GET Done? (extra get_task_struct) | PUT Done? (put_task_struct) | Balanced for extra get? | Notes |
|------|-------------|-----------------------------------|----------------------------|-------------------------|-------|
| 1443 | early return 0 | N/A (before any task) | N/A | ✅ | no task struct |
| 1449 | early return 0 | N/A | N/A | ✅ | no task struct |
| 1456 | return err | N/A | N/A | ✅ | no task struct |
| 1468 (goto fini) | error return | N/A | N/A | ✅ | no task struct |
| 1477 (goto out_obj) | error return | N/A | N/A | ✅ | no task struct |
| 1487 (goto out_obj) | error return | N/A | N/A | ✅ | no task struct |
| 1498 (goto out_obj) | error return (after i915_vma_pin fail) | N/A | N/A | ✅ | tsk not yet created |
| 1510 (goto out_obj) | error return (after fence pin fail) | N/A | N/A | ✅ | tsk not yet created |
| 1519 (goto out_obj) | error return (move_to_active fail?) | N/A | N/A | ✅ | tsk not yet created |
| 1525 (goto out_rq) | error return (after if(err) goto out_rq before thread) | N/A | N/A | ✅ | tsk not yet created |
| 1573 (tsk IS_ERR → tsk=NULL, goto out_reset) | error return via out_reset | NO (get not called) | NO (tsk NULL) | ✅ | tsk is NULL, no ref taken |
| 1578 (successful kthread_run + get_task_struct, then fall‑through or error goto out_reset) | either fall‑through or goto out_reset due to wait_for failure, then return via out_reset → out_rq | YES (get_task_struct called) | YES (put_task_struct called inside `if(tsk)` block) | ✅ for the extra get | BUT **initial reference from `kthread_run` is NOT released** after `put_task_struct`. That initial ref is leaked. |
| - (fall‑through from successful thread to out_reset) | return via out_reset → out_rq | YES | YES (inside if) | ✅ for extra get | Initial ref leaked |
| L1584 (goto out_reset after wait_for failure) | return via out_reset → out_rq | YES | YES (inside if) | ✅ for extra get | Initial ref leaked |

**Analysis**:
- The `get_task_struct(tsk)` (line 1578) adds one extra reference. This extra reference is correctly paired with the `put_task_struct(tsk)` inside the `if (tsk)` block at the `out_reset` label.
- However, the `kthread_run` itself returns a `task_struct` **with an initial reference** that the caller owns. This initial reference is **never released** in the function. After stopping the kthread with `kthread_stop(tsk)`, the function must call `put_task_struct(tsk)` once more to drop that initial reference. It only calls it once (matching the extra `get_task_struct`), leaving the original ref held. The local `tsk` pointer is lost on return, causing a permanent refcount leak.
- No ownership transfer or deferred release pattern accounts for the missing put.

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
`__igt_reset_evict_vma()` leaks the initial reference from `kthread_run` because after calling `kthread_stop(tsk)` and `put_task_struct(tsk)` (which only releases the extra `get_task_struct` reference), the original reference is never dropped
```
