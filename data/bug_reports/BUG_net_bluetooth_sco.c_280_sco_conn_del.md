# REAL BUG: net/bluetooth/sco.c:280 sco_conn_del()

**Confidence**: HIGH | **Counter**: `conn->ref.refcount.refs.counter`

## Reasoning

| L281 | implicit return (success) | YES | YES (L268 only) | ✅ | single put matches single get |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L261 | early return (!conn) | NO (get failed) | N/A | ✅ | hold_unless_zero returned NULL, no ref held |
| L272 | error return (!sk) | YES (hold succeeded) | YES (L268) + YES (L271) | ❌ EXCESS PUT | double sco_conn_put, only one get |
| L281 | implicit return (success) | YES | YES (L268 only) | ✅ | single put matches single get |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On sk==NULL path, sco_conn_put is called twice (L268 and L271) while only one reference was taken via sco_conn_hold_unless_zero (L259), causing an excess put.
```
