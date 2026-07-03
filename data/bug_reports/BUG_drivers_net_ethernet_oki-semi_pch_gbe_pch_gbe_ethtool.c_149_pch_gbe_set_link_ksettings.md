# REAL BUG: drivers/net/ethernet/oki-semi/pch_gbe/pch_gbe_ethtool.c:149 pch_gbe_set_link_ksettings()

**Confidence**: MEDIUM | **Counter**: `$->irq_sem.counter`

## Reasoning

| L149 (if netif_running false) | success | NO | NO | ✅ | else block calls pch_gbe_reset, no get/put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L133 | error (mii set fails) | NO | N/A | ✅ | pch_gbe_down not called |
| L149 (if netif_running true, pch_gbe_up success) | success | YES (pch_gbe_down called) | YES (pch_gbe_up releases) | ✅ | |
| L149 (if netif_running true, pch_gbe_up error) | error | YES (pch_gbe_down acquired) | NO (pch_gbe_up may not release on error) | ❌ LEAK | smatch warns refcount leak on irq_sem.counter at this return |
| L149 (if netif_running false) | success | NO | NO | ✅ | else block calls pch_gbe_reset, no get/put |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

pch_gbe_down(adapter) acquires irq_sem; if pch_gbe_up(adapter) returns an error (L149), the semaphore is not released, causing a refcount leak. Without pch_gbe_up source, the exact error path is unconfirmed, but the function’s design (return ret directly) makes a leak highly likely, matching smatch’s report.
```
