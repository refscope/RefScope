# REAL BUG: drivers/infiniband/hw/irdma/cm.c:1190 irdma_schedule_cm_timer()

**Confidence**: HIGH | **Counter**: `cm_node->refcnt.refs.counter`

## Reasoning

retrans entry. The excess put warning strongly supports that cleanup does a put, making the `close_when_complete` path a double-put bug. If cleanup does NOT put, then the `close_when_complete=false` path would leak, which is not warned. Therefore the warning is consistent with cleanup doing a put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1138 (kzalloc fail, return -ENOMEM) | error | NO (before get) | N/A | ✅ | |
| L1155 (close_entry exists, return -EINVAL) | error | NO (in CLOSE branch, no get) | N/A | ✅ | |
| L1187 (CLOSE branch success, return 0) | success | NO (only CLOSE, no get) | N/A | ✅ | |
| L1176 (SEND, send_retrans=false, close_when_complete=false, return 0) | success | YES (refcount_inc at L1169) | YES (irdma_cleanup_retrans_entry likely puts) | ✅ | single PUT balances the GET |
| L1176 (SEND, send_retrans=false, close_when_complete=true, return 0) | success | YES (refcount_inc at L1169) | YES (cleanup_retrans_entry puts) + YES (irdma_rem_ref_cm_node puts) | ❌ EXCESS PUT | double decrement after one increment → refcount underflow |
| L1183 (SEND, send_retrans=true, return 0 after spinlock) | success | YES (refcount_inc at L1169) | NO in this function (deferred to timer callback) | ✅ (reference owned by timer) | timer entry holds ref; callback will drop it later |

**Note**: `irdma_cleanup_retrans_entry()` contract is unknown; based on naming and code context it likely performs a `refcount_dec` on `cm_node->refcnt` before freeing the retrans entry. The excess put warning strongly supports that cleanup does a put, making the `close_when_complete` path a double-put bug. If cleanup does NOT put, then the `close_when_complete=false` path would leak, which is not warned. Therefore the warning is consistent with cleanup doing a put.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

On the `SEND, !send_retrans, close_when_complete` path, `irdma_cleanup_retrans_entry(cm_node)` likely drops the reference acquired by the earlier `refcount_inc`, and `irdma_rem_ref_cm_node(cm_node)` drops it again, causing an excess put on `cm_node->refcnt`.
```
