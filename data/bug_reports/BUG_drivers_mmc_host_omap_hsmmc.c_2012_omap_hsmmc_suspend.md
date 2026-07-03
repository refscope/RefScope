# REAL BUG: drivers/mmc/host/omap_hsmmc.c:2012 omap_hsmmc_suspend()

**Confidence**: HIGH | **Counter**: `host->dev->power.usage_count.counter`

## Reasoning

| 2012 | normal return | CONDITIONAL (get can fail) | YES (unconditional) | ❌ **EXCESS PUT** | pm_runtime_get_sync return not checked; if it returns <0, no ref is taken but put_sync still decrements → underflow |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 1997 | early return (host==NULL) | NO (before get) | N/A | ✅ | no get, no put |
| 2012 | normal return | CONDITIONAL (get can fail) | YES (unconditional) | ❌ **EXCESS PUT** | pm_runtime_get_sync return not checked; if it returns <0, no ref is taken but put_sync still decrements → underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` return value is not checked; if it fails (<0) the runtime PM usage count is not incremented, but `pm_runtime_put_sync` is called unconditionally, leading to a refcount underflow (excess put).
```
