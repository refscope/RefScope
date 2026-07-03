# REAL BUG: net/tipc/topsrv.c:611 tipc_topsrv_kern_unsubscr()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L611 (end of function) | implicit return after two conn_put | YES (tipc_conn_lookup succeeded) | YES (2 puts) | ❌ EXCESS PUT | One get from lookup, but two conn_put calls → double-put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L605 | return (con==NULL) | NO (tipc_conn_lookup returned NULL) | N/A  | ✅ | Safe return, no get, no put |
| L611 (end of function) | implicit return after two conn_put | YES (tipc_conn_lookup succeeded) | YES (2 puts) | ❌ EXCESS PUT | One get from lookup, but two conn_put calls → double-put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
tipc_conn_lookup conditionally acquires one kref, but the success path calls conn_put twice, releasing one extra reference and triggering the excess‑put warning.
```
