# REAL BUG: sound/soc/stm/stm32_spdifrx.c:1038 stm32_spdifrx_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L1015 (via L995/L998) | error | YES | NO | ❌ LEAK | remove() does not assert; probe failure aborts device binding, so no later remove |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L961 | early error (parse_of fail) | NO (before get) | N/A | ✅ | |
| L967 | early error (regmap init fail) | NO (before get) | N/A | ✅ | |
| L974 | early error (IRQ fail) | NO (before get) | N/A | ✅ | |
| L979 | early error (reset get fail) | NO (before get) | N/A | ✅ | |
| L988 | error (PCM register fail) | YES (deassert at L984) | NO | ❌ LEAK | No assert on this path |
| L992 | error (component register fail) | YES | NO | ❌ LEAK | snd_dmaengine_pcm_unregister does not assert |
| L995 → L1015 | error (dma_ctrl_register fail) | YES | NO | ❌ LEAK | stm32_spdifrx_remove has no access to `rst` (local variable), cannot assert |
| L998 → L1015 | error (regmap read fail) | YES | NO | ❌ LEAK | same as above |
| L1011 | success | YES | NO (held for lifetime) | ✅ | Reset deasserted for device lifetime; will be asserted in remove() on normal unload |
| L1015 (via L995/L998) | error | YES | NO | ❌ LEAK | remove() does not assert; probe failure aborts device binding, so no later remove |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
reset_control_deassert() at L984 increments deassert_count, but three error returns (PCM register fail, component register fail, and goto error) never call reset_control_assert() — the local `rst` is not stored, so stm32_spdifrx_remove() cannot release it.```
```
