# REAL BUG: security/yama/yama_lsm.c:386 yama_ptrace_access_check()

**Confidence**: LOW | **Counter**: `$->usage.refs.counter`

## Reasoning

rding to smatch leak) | ❌ LEAK (when `report_access` executes) | The only return path. `report_access` is called when `rc != 0 && (mode & PTRACE_MODE_NOAUDIT) == 0`. It internally does `get_task_struct`, but the smatch warning indicates no matching `put` before it returns, leaking the reference. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L387 | return rc   | YES (if `report_access` called) | NO (put not performed inside `report_access`, according to smatch leak) | ❌ LEAK (when `report_access` executes) | The only return path. `report_access` is called when `rc != 0 && (mode & PTRACE_MODE_NOAUDIT) == 0`. It internally does `get_task_struct`, but the smatch warning indicates no matching `put` before it returns, leaking the reference. |

VERDICT: REAL_BUG
CONFIDENCE: LOW
`report_access` acquires a task_struct reference (as per contracts) but fails to release it, leaking the reference on the error path; the caller does not own the reference and cannot fix the imbalance. Without `report_access` source, confidence is low but consistent with the smatch warning.
```
