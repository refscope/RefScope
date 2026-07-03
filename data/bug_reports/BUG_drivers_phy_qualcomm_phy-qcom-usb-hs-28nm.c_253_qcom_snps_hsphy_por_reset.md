# REAL BUG: drivers/phy/qualcomm/phy-qcom-usb-hs-28nm.c:253 qcom_snps_hsphy_por_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

ro, balanced                           |
| L251 | success     | YES (deassert called unconditionally)| YES       | ✅         | assert dec, deassert inc — net zero, balanced                           |

## Full Response

```
| Line | Return Type | GET Done?                            | PUT Done? | Balanced? | Notes                                                                   |
|------|-------------|--------------------------------------|-----------|-----------|-------------------------------------------------------------------------|
| L225 | error       | NO (deassert not reached)            | YES       | ❌ LEAK    | assert decrements counter, no inc — underflow on this path              |
| L242 | error       | YES (deassert called unconditionally)| YES       | ✅         | assert dec, deassert inc — net zero, balanced                           |
| L251 | success     | YES (deassert called unconditionally)| YES       | ✅         | assert dec, deassert inc — net zero, balanced                           |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Call to reset_control_assert (unconditional put) at L223; if it returns error, the function returns without calling reset_control_deassert (unconditional get), leaving deassert_count decremented and causing an eventual underflow (excess put).
```
