# REAL BUG: drivers/infiniband/hw/irdma/cm.c:1372 irdma_cm_timer_tick()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L1342-L1346 (send_retrans false) → free_retrans_entry, possible extra rem_ref, done | loop end | YES | 2 or 3 puts (free_retrans_entry + cond rem_ref + L1372) | ❌ LEAK | Triple-put if close_when_complete |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1300 (goto done, send_entry NULL) | loop iteration end | YES (list prep ref) | 1 put at L1372 | ✅ | Normal balance |
| L1303-L1309 (time_after, state != OFFLOADED) → done | loop end | YES | 1 put at L1372 | ✅ | No extra puts |
| L1308 (time_after, state == OFFLOADED) → free_retrans_entry, done | loop end | YES | free_retrans_entry refcount_dec + L1372 put = 2 | ❌ LEAK | irdma_free_retrans_entry decrements refcount, then L1372 puts again |
| L1314-L1315 (state OFFLOADED/CLOSED) → free_retrans_entry, done | loop end | YES | 2 puts (free_retrans_entry + L1372) | ❌ LEAK | Same double-put |
| L1319-L1325 (retranscount/retrycount zero) → free_retrans_entry, retrans_expired, done | loop end | YES (+ possible incs from retrans_expired) | 2 puts (free_retrans_entry + L1372) | ❌ LEAK | Double-put, retrans_expired may offset but net excess |
| L1336 (send_retrans true) → fallthrough done | loop end | YES | 1 put at L1372 | ✅ | Normal |
| L1342-L1346 (send_retrans false) → free_retrans_entry, possible extra rem_ref, done | loop end | YES | 2 or 3 puts (free_retrans_entry + cond rem_ref + L1372) | ❌ LEAK | Triple-put if close_when_complete |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Multiple paths call irdma_free_retrans_entry (which decrements cm_node's refcount) and then unconditionally hit L1372 irdma_rem_ref_cm_node, causing a refcount double-put and triggering the excess put warning.
```
