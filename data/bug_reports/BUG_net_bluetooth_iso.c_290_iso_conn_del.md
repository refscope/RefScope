# REAL BUG: net/bluetooth/iso.c:290 iso_conn_del()

**Confidence**: HIGH | **Counter**: `conn->ref.refcount.refs.counter`

## Reasoning

| fallthrough (sk valid) | function end | YES | YES (line 279 temp put only) | ✅ | original ref remains, will be dropped by caller later |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L271 | early return (conn NULL) | NO (hold_unless_zero returned NULL) | N/A | ✅ | no ref held |
| L283 | return on !sk        | YES (hold_unless_zero succeeded) | YES (line 279 temp put + line 282 extra put) | ❌ EXCESS PUT | extra iso_conn_put drops hcon's reference prematurely |
| fallthrough (sk valid) | function end | YES | YES (line 279 temp put only) | ✅ | original ref remains, will be dropped by caller later |
```

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`iso_conn_del()` temporarily increments the refcount with `iso_conn_hold_unless_zero()` and correctly balances it with `iso_conn_put()` at line 279 after locking. However, on the `sk == NULL` error path, it performs an *extra* `iso_conn_put()` at line 282, which drops the `hcon`'s own reference too early. The caller (e.g., `hci_conn_del`) will later also `iso_conn_put()`, causing a double-free / use-after-free. The warning reports an excess put, matching this double drop.
```
