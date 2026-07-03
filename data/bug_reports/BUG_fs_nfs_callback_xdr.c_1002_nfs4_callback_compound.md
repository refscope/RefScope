# REAL BUG: fs/nfs/callback_xdr.c:1002 nfs4_callback_compound()

**Confidence**: MEDIUM | **Counter**: `$->cl_count.refs.counter`

## Reasoning

| L1007 (`out_invalidcred`) | `return rpc_success` | YES/NO (depends) | YES (already put before goto) | ✅ | reached only after explicit put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L948 (decode fail) | `rpc_garbage_args` | NO (no get) | N/A | ✅ | |
| L961 (`!cps.clp`) | `goto out_invalidcred` | NO (NULL return) | N/A | ✅ | no ref held |
| L968 (`!check_gss`) | `goto out_invalidcred` | YES (get succeeded) | YES (explicit put before goto) | ✅ | |
| L975 (encode fail, cps.clp non‑NULL) | `return rpc_system_err` | YES | YES (put inside `if`) | ✅ | |
| L975 (encode fail, cps.clp NULL) | `return rpc_system_err` | NO | NO (skip put) | ✅ | |
| L993 (success path) | `return rpc_success` | YES (if minorversion==0) | YES (line 1002) | ⚠️ SUSPECT DOUBLE PUT | **nfs4_cb_free_slot** likely releases the slot reference → an implicit put on cps.clp. Then explicit `nfs_put_client` at L1002 causes an extra put. Warning location matches this line. |
| L1007 (`out_invalidcred`) | `return rpc_success` | YES/NO (depends) | YES (already put before goto) | ✅ | reached only after explicit put |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The final `nfs_put_client(cps.clp)` at line 1002 is likely a double‑put: `nfs4_cb_free_slot(&cps)` already releases the client reference held by the callback slot, making the explicit put redundant and triggering the observed refcount excess.
```
