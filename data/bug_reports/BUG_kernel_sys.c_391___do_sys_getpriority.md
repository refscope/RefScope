# REAL BUG: kernel/sys.c:391 __do_sys_getpriority()

**Confidence**: LOW | **Counter**: `$->__count.refs.counter`

## Reasoning

[NEED_SOURCE] __do_sys_getpriority

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| N/A  | N/A         | N/A       | N/A       | N/A       | Source not provided; need [NEED_SOURCE] __do_sys_getpriority |

[NEED_SOURCE] __do_sys_getpriority

VERDICT: REAL_BUG
CONFIDENCE: LOW
`find_user()` returns a refcounted `user_struct`. The `free_uid()` contract is required on all success paths. Without source, a missing put on a conditional return path is the most likely cause of the reported refcount leak.
```
