# REAL BUG: drivers/mmc/host/sh_mmcif.c:1112 sh_mmcif_set_ios()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L1119 | normal return (MMC_POWER_OFF, host->power false) | NO | NO | ✅ | No refcount ops |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1071 | early return (host->state != STATE_IDLE) | NO (before get) | N/A | ✅ | No get/put executed |
| L1119 | normal return (MMC_POWER_UP, host->power false) | YES (pm_runtime_get_sync) | NO (held) | ⚠️ Intentionally held, but GET return unchecked; if GET fails, host->power still true → future excess put |
| L1119 | normal return (MMC_POWER_UP, host->power true) | NO | NO | ✅ | Already powered |
| L1119 | normal return (MMC_POWER_ON) | NO | NO | ✅ | No refcount ops |
| L1119 | normal return (MMC_POWER_OFF, host->power true) | NO (in this call) | YES (pm_runtime_put at L1112) | ❌ **EXCESS PUT if prior GET failed** | PUT executed; if earlier GET did not inc counter, counter goes negative |
| L1119 | normal return (MMC_POWER_OFF, host->power false) | NO | NO | ✅ | No refcount ops |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
pm_runtime_get_sync() return value is not checked, but host->power is set to true unconditionally; if get fails, later pm_runtime_put() causes an excess put on a zero usage_count.
```
