# REAL BUG: kernel/uid16.c:200 __do_sys_setgroups16()

**Confidence**: LOW | **Counter**: `group_info->usage.refs.counter`

## Reasoning

| Source not provided; unable to enumerate return paths. Contracts show `groups_alloc()` (unconditional GET) initialises `group_info` with refcount 1. Leak warning at line 200 strongly suggests an error path after `groups_alloc()` that does not call `put_group_info()`/`refcount_dec_and_test()`. |

## Full Response

```
[NEED_SOURCE] __do_sys_setgroups16

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| N/A  | N/A         | N/A       | N/A       | N/A       | Source not provided; unable to enumerate return paths. Contracts show `groups_alloc()` (unconditional GET) initialises `group_info` with refcount 1. Leak warning at line 200 strongly suggests an error path after `groups_alloc()` that does not call `put_group_info()`/`refcount_dec_and_test()`. |

VERDICT: REAL_BUG
CONFIDENCE: LOW
`groups_alloc()` unconditionally creates a reference-counted object; without source, the leak warning at line 200 implies an error return that omits the required `put_group_info()` call.
```
