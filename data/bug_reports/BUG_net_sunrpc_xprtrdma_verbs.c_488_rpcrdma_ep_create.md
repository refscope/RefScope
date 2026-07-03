# REAL BUG: net/sunrpc/xprtrdma/verbs.c:488 rpcrdma_ep_create()

**Confidence**: HIGH | **Counter**: `ep->re_kref.refcount.refs.counter`

## Reasoning

| L470 (return 0) | success | YES (initial ref from kref_init) | NO (intentional – ownership transferred to r_xprt->rx_ep) | ✅ (ownership transferred) | Stored in rx_ep; later put via rpcrdma_xprt cleanup. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L384 (if (!ep)) | error (return -ENOTCONN) | NO (before kref_init) | N/A | ✅ | allocation failure, no object. |
| L390-391 (IS_ERR(id)) | error (return PTR_ERR(id)) | YES (kref_init at L386) | NO (uses kfree, not rpcrdma_ep_put) | ❌ LEAK | kref_init set refcount to 1, then memory freed directly without kref_put. Violates contract: kref_init must be paired with exactly one kref_put. |
| L405 (goto out_destroy) | error (frwr_query_device) | YES | YES (out_destroy calls rpcrdma_ep_put) | ✅ | |
| L418 (goto out_destroy) | error (send_cq alloc) | YES | YES | ✅ | |
| L425 (goto out_destroy) | error (recv_cq alloc) | YES | YES | ✅ | |
| L462 (goto out_destroy) | error (ib_alloc_pd) | YES | YES | ✅ | |
| L467 (goto out_destroy) | error (rdma_create_qp) | YES | YES | ✅ | |
| L470 (return 0) | success | YES (initial ref from kref_init) | NO (intentional – ownership transferred to r_xprt->rx_ep) | ✅ (ownership transferred) | Stored in rx_ep; later put via rpcrdma_xprt cleanup. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
kref_init establishes the initial reference at L386; the error path at L390-391 frees the object directly with kfree without calling rpcrdma_ep_put, leaving the refcount dangling and violating the contractual requirement to pair every kref_init with exactly one kref_put.
```
