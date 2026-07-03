# REAL BUG: drivers/misc/fastrpc.c:1271 fastrpc_internal_invoke()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1250 (success path → bail) | success (return 0) | YES | YES (err==0) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1200 (early) | error (-EINVAL) | NO (before alloc) | N/A | ✅ | |
| L1202 (early) | error (-EPIPE) | NO (before alloc) | N/A | ✅ | |
| L1205 (early) | error (-EPERM) | NO (before alloc) | N/A | ✅ | |
| L1209 (alloc failure) | error (IS_ERR) | NO (alloc failed) | N/A | ✅ | no ref |
| L1214 (get_args error → bail) | error (goto bail) | YES (alloc succeeded) | YES (likely, unless err is -ERESTARTSYS / -ETIMEDOUT) | ✅ (typically) | `fastrpc_get_args` unlikely to return those two codes |
| L1220 (invoke_send error → bail) | error (goto bail) | YES | NO if err==-ERESTARTSYS | ❌ **LEAK** | `invoke_send` can return -ERESTARTSYS; bail skips `fastrpc_context_put` |
| L1224 (kernel timeout → bail) | error (goto bail) | YES | NO (err==-ETIMEDOUT) | ❌ **LEAK** | explicit -ETIMEDOUT avoids put |
| L1225 (user interruptible → bail) | error (goto bail) | YES | NO (err==-ERESTARTSYS) | ❌ **LEAK** | `wait_for_completion_interruptible` returns -ERESTARTSYS |
| L1235 (put_args error → bail) | error (goto bail) | YES | NO if err==-ERESTARTSYS / -ETIMEDOUT | ⚠️ Possible LEAK | depends on `fastrpc_put_args` return |
| L1240 (ctx->retval error → bail) | error (goto bail) | YES | NO if err==-ERESTARTSYS / -ETIMEDOUT | ⚠️ Possible LEAK | `ctx->retval` could be either |
| L1250 (success path → bail) | success (return 0) | YES | YES (err==0) | ✅ | |

**VERDICT: REAL_BUG**

**CONFIDENCE: HIGH**

`fastrpc_context_alloc` unconditionally gives a reference.  On paths where `err` becomes `-ETIMEDOUT` or `-ERESTARTSYS`, the `bail` label skips `fastrpc_context_put(ctx)`, leaking the reference (and any extra reference taken by `fastrpc_invoke_send`).  The warning is accurate.
```
