# REAL BUG: kernel/locking/rwsem.c:1132 rwsem_down_read_slowpath()

**Confidence**: MEDIUM | **Counter**: `$->usage.refs.counter`

## Reasoning

| ⚠️ suspect PUT (the warning says excess put at this line) | ❌ excess put | no get_task_struct for current in this function; if `rwsem_del_wake_waiter` does `put_task_struct(current)`, that’s an unmatched put → excess put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1052 (optimistic steal, `return sem`) | success | YES (if `rwsem_mark_wake` called; it does get_task_struct on woken tasks, added to wake_q) | YES (via `wake_up_q` at L1051) | ✅ | GETs balanced by wake_q flush |
| L1074 (empty queue fast return) | success | NO | N/A | ✅ | no get calls |
| L1108 (normal wake after loop) | success | NO explicit (woken externally; get/put handled by the waker's wake_q) | N/A | ✅ | no ref held in this function |
| L1131 (signal `out_nolock` → `ERR_PTR(-EINTR)`) | error | ? (unknown, `rwsem_del_wake_waiter` may PUT but no visible GET) | ⚠️ suspect PUT (the warning says excess put at this line) | ❌ excess put | no get_task_struct for current in this function; if `rwsem_del_wake_waiter` does `put_task_struct(current)`, that’s an unmatched put → excess put |

[NEED_SOURCE] rwsem_del_wake_waiter
[NEED_SOURCE] rwsem_cond_wake_waiter

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
In `rwsem_down_read_slowpath`, the `out_nolock` path calls `rwsem_del_wake_waiter()` which likely performs a `put_task_struct` on the current task (the warning shows excess put on usage.refs.counter). No matching `get_task_struct(current)` occurs in this function (waiter is on-stack, no ref taken at enqueue). Unless the callee does a matching get internally, this is an unmatched put causing a refcount underflow.

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] rwsem_mark_wake
[NEED_SOURCE] rwsem_cond_wake_waiter

--- [NEED_SOURCE r2] ---

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1052 (optimistic steal) | success | YES (if `rwsem_mark_wake` fires → get_task_struct on woken tasks) | YES (via `wake_up_q` at L1051) | ✅ | gets balanced by wake_q flush |
| L1074 (empty queue fast return) | success | NO | N/A | ✅ | no get |
| L1108 (normal wake after loop) | success | NO | N/A | ✅ | no get on current task |
| L1131 (`out_nolock` → `ERR_PTR(-EINTR)`) | error | NO | NO (see note) | ✅ | `rwsem_del_wake_waiter` only wakes other waiters via `wake_up_q`; it does NOT perform `put_task_struct(current)`. No ref imbalance on this path. |

VERDICT: FALSE_POSITIVE  
CONFIDENCE: HIGH  
The `out_nolock` path does not contain a `put_task_struct` call; `rwsem_del_wake_waiter` just removes the waiter from the list and wakes other tasks, so it cannot cause a refcount underflow on the current task. The reported excess put does not originate from this error path.
```
