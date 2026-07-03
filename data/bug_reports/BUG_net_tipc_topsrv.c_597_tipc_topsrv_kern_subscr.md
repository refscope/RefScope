# REAL BUG: net/tipc/topsrv.c:597 tipc_topsrv_kern_subscr()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L597 (rc == 0 path) | success | YES         | YES (one put)      | ✅               | only the unconditional `conn_put(con)` at L597 |

## Full Response

```
| Line | Return Type | GET Done?   | PUT Done?          | Balanced?       | Notes |
|------|-------------|-------------|--------------------|-----------------|-------|
| L583 | error       | NO (con is ERR_PTR) | N/A                | ✅               | IS_ERR guard, no ref held |
| L590-591 (rc != 0 path) | error | YES         | YES (two puts)     | ❌ EXCESS PUT    | `conn_put(con)` inside `if (rc)` block **and** unconditional `conn_put(con)` at L597 |
| L597 (rc == 0 path) | success | YES         | YES (one put)      | ✅               | only the unconditional `conn_put(con)` at L597 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the error path after `tipc_conn_rcv_sub()` fails, `tipc_topsrv_kern_subscr()` calls `conn_put()` inside the `if (rc)` block **and** again unconditionally at the end, resulting in a double release of the `tipc_conn` reference obtained from `tipc_conn_alloc()`. This over-decrements the `kref` and leads to the refcount excess put.
```
