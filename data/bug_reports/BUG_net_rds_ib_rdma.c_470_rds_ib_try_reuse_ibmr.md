# REAL BUG: net/rds/ib_rdma.c:470 rds_ib_try_reuse_ibmr()

**Confidence**: HIGH | **Counter**: `pool->item_count.counter`

## Reasoning

| return ibmr (after rds_ib_flush_mr_pool, dec) | success (ibmr) | YES then PUT | YES  | ✅ | inc and dec balance |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| return ibmr (after rds_ib_reuse_mr) | success (ibmr) | NO (before inc) | N/A  | ✅ | no get    |
| break (inc ≤ max_items) → return NULL | error (NULL) | YES (atomic_inc_return) | NO   | ❌ LEAK | inc without dec, returns NULL |
| break (inc > max, dec, iter > 2) → return NULL | error (NULL) | YES then PUT (dec) | YES  | ✅ | inc and dec balance |
| return ibmr (after rds_ib_flush_mr_pool, dec) | success (ibmr) | YES then PUT | YES  | ✅ | inc and dec balance |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
atomic_inc_return increments item_count; when result ≤ max_items the function breaks and returns NULL without matching atomic_dec, leaking the reference.
```
