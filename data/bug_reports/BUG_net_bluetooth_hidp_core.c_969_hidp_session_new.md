# REAL BUG: net/bluetooth/hidp/core.c:969 hidp_session_new()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| 963  | success (0)   | N/A (caller handles) | N/A (caller will put) | ✅ | session transferred to *out |

## Full Response

```
| Line | Return Type | GET Done? (session->ref) | PUT Done? (kref_put) | Balanced? | Notes |
|------|-------------|--------------------------|----------------------|-----------|-------|
| 913  | error (-ENOMEM) | NO (before kref_init) | N/A | ✅ | kref_init not called |
| 956  | goto err_free | YES (kref_init at L924) | NO (kfree without kref_put) | ❌ LEAK | err_free: only l2cap_conn_put and kfree |
| 963  | success (0)   | N/A (caller handles) | N/A (caller will put) | ✅ | session transferred to *out |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
kref_init sets session->ref to 1; the error path at hidp_session_dev_init failure jumps to err_free, which frees session via kfree without kref_put, leaking the reference count.
```
