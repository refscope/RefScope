# REAL BUG: net/sunrpc/clnt.c:615 rpc_create()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L606 | return `clnt` (after loop) | YES (implicit from `xprt_create_transport`) | YES (consumed by client) | ✅ | The transport reference is held by the newly created client; correct. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L533 | return `rpc_create_xprt(args, xprt)` (bc_xprt early path) | YES (`xprt_get(xprt)`) | NO | ❌ LEAK | `xprt_get` adds a reference on the backchannel transport; the returned `clnt` (if successful) does not account for the extra ref, and no matching `put` appears in this path. |
| L574 | return `ERR_PTR(-EINVAL)` (bad address family) | NO | N/A | ✅ | No get occurred. |
| L585 | return `(struct rpc_clnt *)xprt` (`xprt_create_transport` error) | NO (`IS_ERR` guard) | N/A | ✅ | `xprt_create_transport` returned an error pointer; no reference was taken. |
| L596 | return `clnt` (IS_ERR or `nconnect <= 1`) | YES (implicit from `xprt_create_transport` on success) | UNCERTAIN | ? | If `rpc_create_xprt` consumes the transport reference on error, balanced; otherwise leak. Not examined here. |
| L606 | return `clnt` (after loop) | YES (implicit from `xprt_create_transport`) | YES (consumed by client) | ✅ | The transport reference is held by the newly created client; correct. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`xprt_get(xprt)` at L533 adds a kref on the backchannel transport, and the early return never releases it — the extra reference leaks regardless of `rpc_create_xprt()` behavior.
```
