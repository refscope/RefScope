# REAL BUG: drivers/spi/spi-rockchip.c:273 rockchip_spi_set_cs()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L266-273 (de-assert branch) | void (function end) | NO  | YES (pm_runtime_put) | ❌ LEAK (cross‑call) | put without prior get if de‑assert called first while CS high |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L254 | void (early return) | NO  | NO  | ✅ | cs_actual == cs_asserted, no get/put |
| L258-264 (assert branch) | void (function end) | YES (pm_runtime_get_sync) | NO  | ⚠️ | get held across calls, expects later put |
| L266-273 (de-assert branch) | void (function end) | NO  | YES (pm_runtime_put) | ❌ LEAK (cross‑call) | put without prior get if de‑assert called first while CS high |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
De‑assert path (L273) unconditionally calls pm_runtime_put. If the first set_cs is `enable=false` while CS is high, the no‑op check (L253) is bypassed, leading to a put without a matching get and a runtime underflow (excess put).
```
