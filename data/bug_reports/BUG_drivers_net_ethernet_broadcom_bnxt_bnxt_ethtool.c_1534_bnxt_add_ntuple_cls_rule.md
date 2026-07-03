# REAL BUG: drivers/net/ethernet/broadcom/bnxt/bnxt_ethtool.c:1534 bnxt_add_ntuple_cls_rule()

**Confidence**: HIGH | **Counter**: `l2_fltr->refcnt.counter`

## Reasoning

| L1538 (ntuple_err) | error return | YES | YES | ✅ | all other error paths → balanced |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1386 | error return | NO (before GET) | N/A | ✅ | |
| L1389 | error return | NO | N/A | ✅ | |
| L1393 | error return | NO | N/A | ✅ | |
| L1398 | error return | NO | N/A | ✅ | |
| L1404 | error return | NO | N/A | ✅ | |
| L1409 | error return | NO | N/A | ✅ | allocation failure before GET |
| L1412 | (not return) | YES (atomic_inc) | - | - | GET executed here |
| goto L1490 → L1538 | error | YES | YES (at ntuple_err) | ✅ | default switch |
| goto L1493 → L1538 | error | YES | YES | ✅ | mask check |
| goto L1501 → L1538 | error | YES | YES | ✅ | existing filter |
| goto L1516 → L1538 | error | YES | YES | ✅ | rss_ctx fail |
| **L1529** | **error return** | **YES** | **NO** | **❌ LEAK** | bnxt_hwrm_cfa_ntuple_filter_alloc failed; **returns directly, skips ntuple_err** |
| L1532 | success return | YES | NO (intentional) | ⚠️ Ownership transfer | filter inserted; reference held for filter lifetime (not a bug) |
| L1538 (ntuple_err) | error return | YES | YES | ✅ | all other error paths → balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

bnxt_hwrm_cfa_ntuple_filter_alloc failure at L1529 returns directly, skipping the ntuple_err label’s atomic_dec and kfree, leaking the l2_fltr refcount and new_fltr memory.
```
