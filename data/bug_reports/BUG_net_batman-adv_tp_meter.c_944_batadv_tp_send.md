# REAL BUG: net/batman-adv/tp_meter.c:944 batadv_tp_send()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

paths reach the `out` label, where `batadv_tp_sender_cleanup(tp_vars)` unconditionally invokes `batadv_tp_vars_put` (releasing the worker’s reference), and then the function itself calls `batadv_tp_vars_put(tp_vars)` again, resulting in an extra decrement that triggers the **refcount excess put**.

## Full Response

```
```
| Line | Return Type | GET (tp_vars ref) Done? | PUT (cleanup) Done? | PUT (explicit) Done? | Balanced? | Notes |
|------|-------------|-------------------------|---------------------|----------------------|-----------|-------|
| L878 (goto out)  | return 0 | YES (worker holds ref) | YES (batadv_tp_sender_cleanup calls batadv_tp_vars_put) | YES (explicit batadv_tp_vars_put(tp_vars)) | ❌ LEAK (excess) | double put on tp_vars |
| L887 (goto out)  | return 0 | YES | YES | YES | ❌ | double put |
| L894 (goto out)  | return 0 | YES | YES | YES | ❌ | double put |
| while break/exit → out | return 0 | YES | YES | YES | ❌ | double put |
| normal loop termination → out | return 0 | YES | YES | YES | ❌ | double put |

All paths reach the `out` label, where `batadv_tp_sender_cleanup(tp_vars)` unconditionally invokes `batadv_tp_vars_put` (releasing the worker’s reference), and then the function itself calls `batadv_tp_vars_put(tp_vars)` again, resulting in an extra decrement that triggers the **refcount excess put**.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`batadv_tp_sender_cleanup` already drops the tp_vars reference; the explicit `batadv_tp_vars_put` at the end is a double‑put, causing a refcount underflow.```
```
