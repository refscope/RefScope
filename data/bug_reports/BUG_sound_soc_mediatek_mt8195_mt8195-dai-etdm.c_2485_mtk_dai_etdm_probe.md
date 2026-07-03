# REAL BUG: sound/soc/mediatek/mt8195/mt8195-dai-etdm.c:2485 mtk_dai_etdm_probe()

**Confidence**: HIGH | **Counter**: `afe->dev->power.usage_count.counter`

## Reasoning

| L2483+ (mclk_freq true, get fails) | success return but get failed | NO (no inc) | YES | ❌ EXCESS PUT | pm_runtime_get_sync return value unchecked; put called after failed get |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2471 (return -EINVAL) | error | NO (before get) | N/A | ✅ | get hasn't happened yet |
| L2477 (mclk_freq false, return 0) | success | NO | N/A | ✅ | no get, no put |
| L2483+ (mclk_freq true, get success) | success | YES | YES | ✅ | balanced pair |
| L2483+ (mclk_freq true, get fails) | success return but get failed | NO (no inc) | YES | ❌ EXCESS PUT | pm_runtime_get_sync return value unchecked; put called after failed get |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync return value not checked; on failure it does not increment usage_count, but the code unconditionally calls pm_runtime_put_sync, causing an excess put.
```
