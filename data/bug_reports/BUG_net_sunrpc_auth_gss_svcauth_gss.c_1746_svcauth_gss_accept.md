# REAL BUG: net/sunrpc/auth_gss/svcauth_gss.c:1746 svcauth_gss_accept()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| PROC_DATA: SVC_DENIED in gc_svc default after get | SVC_DENIED | YES | YES | ✅ | (get happened before auth_err) |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| auth_err (before rsci assignment)      | SVC_DENIED | NO (no rsci) | N/A (rsci==NULL) | ✅ | |
| PROC_INIT/CONTINUE_INIT direct return  | SVC_OK      | NO (no rsci) | N/A               | ✅ | |
| auth_err after rsci obtained (SVC_DENIED from verify) | SVC_DENIED | NO | YES | ❌ EXCESS PUT | `cache_get` never called before `cache_put` |
| drop → out (SVC_DROP from verify)      | SVC_CLOSE   | NO | YES | ❌ EXCESS PUT | |
| PROC_DESTROY: encode_verf fail → auth_err | SVC_DENIED | NO | YES | ❌ EXCESS PUT | |
| PROC_DESTROY: set_accept_stat fail → auth_err | SVC_DENIED | NO | YES | ❌ EXCESS PUT | |
| PROC_DESTROY: success → complete → out | SVC_COMPLETE| NO | YES | ❌ EXCESS PUT | `sunrpc_cache_unhash` may also put, making double put worse |
| PROC_DATA: encode_verf/set_accept_stat fail → auth_err (before `cache_get`) | SVC_DENIED | NO | YES | ❌ EXCESS PUT | |
| PROC_DATA: paths after `cache_get` (normal out, garbage_args, auth_err in gc_svc default) | SVC_OK/SVC_GARBAGE | YES | YES | ✅ | |
| PROC_DATA: SVC_DENIED in gc_svc default after get | SVC_DENIED | YES | YES | ✅ | (get happened before auth_err) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`gss_svc_searchbyctx` returns rsci without a ref; the explicit `cache_get` in PROC_DATA proves it. Many error paths in PROC_DESTROY and PROC_DATA (before `cache_get`) call `cache_put` at `out:` without a prior `cache_get`, causing excess put.
```
