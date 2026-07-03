# REAL BUG: net/sunrpc/clnt.c:447 rpc_new_client()

**Confidence**: HIGH | **Counter**: `$->xps_kref.refcount.refs.counter`

## Reasoning

| Success (return clnt) | success | YES | YES (once, at ~L447) | ✅ | Normal release of caller's ref after acquiring internal reference. |

## Full Response

```
| Line | Return Type | GET Done? (xprt_iter_init) | PUT Done? (xprt_switch_put) | Balanced? | Notes |
|------|-------------|---------------------------|-----------------------------|-----------|-------|
| rpciod_up() fail → out_no_rpciod (early error) | error | NO | YES (once, at out_no_rpciod) | Probably balanced (caller ref released) | No internal get, but caller ref held; by design. |
| args->version too high → out_err → out_no_rpciod | error | NO | YES | Same | |
| version == NULL → out_err → out_no_rpciod | error | NO | YES | Same | |
| kzalloc_obj() fails → out_err → out_no_rpciod | error | NO | YES | Same | |
| rpc_alloc_clid() fails → out_no_clid → … out_no_rpciod | error | NO | YES | Same | |
| clnt->cl_metrics == NULL → out_no_stats → … out_no_rpciod | error | NO | YES | Same | |
| **rpc_client_register() fails** → out_no_path → … out_no_rpciod | error | **YES** (xprt_iter_init already called) | **YES (at ~L447) + YES (again at out_no_rpciod)** | **❌ EXCESS PUT – refcount underflow** | First put already dropped caller's ref; second put is a double-free / UAF risk. |
| Success (return clnt) | success | YES | YES (once, at ~L447) | ✅ | Normal release of caller's ref after acquiring internal reference. |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

The function drops the caller’s reference to `xps` via `xprt_switch_put()` early (around line 447). Later, if `rpc_client_register()` fails, the error path falls through to `out_no_rpciod` which calls `xprt_switch_put()` again on the same `xps`, leading to a double put and a refcount underflow (use-after-free).
```
