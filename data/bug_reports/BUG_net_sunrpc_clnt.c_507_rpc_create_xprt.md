# REAL BUG: net/sunrpc/clnt.c:507 rpc_create_xprt()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L507 | success (return clnt) | YES (xps reference owned by client) | N/A (client lifetime) | ✅ | ownership transferred to client on success |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L462 | error (xps alloc fail) | NO (xps NULL) | N/A (xprt_put done) | ✅ | xprt_switch_alloc returned NULL, no xps ref held |
| L471 | error (IS_ERR(clnt)) | YES (xprt_switch_get or xprt_switch_alloc succeeded) | NO | ❌ LEAK | rpc_new_client failed, xps reference not released |
| L477 | error (rpc_ping fail) | YES (xps reference held by client) | YES (rpc_shutdown_client) | ✅ | client shutdown releases all client-held resources |
| L483 | error (rpc_ping_noreply fail) | YES (same) | YES (rpc_shutdown_client) | ✅ | same |
| L507 | success (return clnt) | YES (xps reference owned by client) | N/A (client lifetime) | ✅ | ownership transferred to client on success |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rpc_new_client` failure (L471) returns without releasing the xps reference obtained via `xprt_switch_alloc` or `xprt_switch_get`. No cleanup path covers this early error return.
```
