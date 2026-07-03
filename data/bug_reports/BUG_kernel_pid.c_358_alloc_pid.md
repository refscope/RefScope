# REAL BUG: kernel/pid.c:358 alloc_pid()

**Confidence**: HIGH | **Counter**: `$->ns.__ns_ref.refs.counter`

## Reasoning

| L176 | success | YES | YES (ownership transferred to struct pid, released later via put_pid) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L21 | error (EINVAL) | NO (before get) | N/A | ✅ | |
| L30-31 | error (ENOMEM) | NO (before get) | N/A | ✅ | |
| L56 | goto out_abort | YES | YES (out_abort calls put_pid_ns) | ✅ | |
| L59 | goto out_abort | YES | YES | ✅ | |
| L129 | goto out_free | YES | YES (out_free falls to out_abort) | ✅ | |
| L142 | goto out_free | YES | YES | ✅ | |
| L160 | goto out_free | YES | YES | ✅ | |
| L170-174 | error (pidfs_add_pid fails) | YES (get_pid_ns at L33, ns_ref_active_get at L168) | NO | ❌ LEAK | free_pid(pid) does not release the initial get_pid_ns(ns) reference; the ns counter is leaked on this path |
| L176 | success | YES | YES (ownership transferred to struct pid, released later via put_pid) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `get_pid_ns(ns)` at line 33 increments the namespace refcount unconditionally. The error path after `pidfs_add_pid()` (line 170-174) calls `free_pid(pid)` but does not call `put_pid_ns(ns)`, and `free_pid` does not handle this top-level reference, causing a refcount leak.
```
