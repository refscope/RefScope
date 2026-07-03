# REAL BUG: net/sunrpc/clnt.c:791 rpc_switch_client_transport()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| ~787 | error (out_revert) | YES (xprt from creation) | YES (xprt_put(xprt)) + implicit put from revert setter | ❌ EXCESS PUT | rpc_clnt_set_transport(clnt, old, ...) likely releases the new transport before assigning old; then xprt_put(xprt) is a double-put causing refcount excess |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~733 | error (IS_ERR) | NO (xprt is ERR, no get) | N/A | ✅ | xprt_create_transport failed |
| ~738 | error (xps NULL) | YES (xprt from creation) | YES (xprt_put) | ✅ | allocation of xps failed, release xprt |
| ~777 | success (return 0) | YES (xprt transferred to client) | NO explicit put | ✅ (assumes rpc_clnt_set_transport consumes ref) | transport owned by client after setter |
| ~787 | error (out_revert) | YES (xprt from creation) | YES (xprt_put(xprt)) + implicit put from revert setter | ❌ EXCESS PUT | rpc_clnt_set_transport(clnt, old, ...) likely releases the new transport before assigning old; then xprt_put(xprt) is a double-put causing refcount excess |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
rpc_clnt_set_transport suspected to release the new transport when reverting to old, making the explicit xprt_put(xprt) in the out_revert path an extra put; the warning matches a double release.
```
