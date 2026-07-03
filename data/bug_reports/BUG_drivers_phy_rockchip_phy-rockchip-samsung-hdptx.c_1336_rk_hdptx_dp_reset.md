# REAL BUG: drivers/phy/rockchip/phy-rockchip-samsung-hdptx.c:1336 rk_hdptx_dp_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L1336 (function exit) | void return | YES (deassert RST_APB → 1 GET)     | YES (assert RST_LANE, RST_CMN, RST_INIT, RST_APB → 4 PUTs)     | ❌ EXCESS PUT | net -3 on deassert_count; asserts on LANE/CMN/INIT lack matching deasserts |

## Full Response

```
```
| Line | Return Type | GET Done?                           | PUT Done?                                                        | Balanced? | Notes |
|------|-------------|-------------------------------------|------------------------------------------------------------------|-----------|-------|
| L1336 (function exit) | void return | YES (deassert RST_APB → 1 GET)     | YES (assert RST_LANE, RST_CMN, RST_INIT, RST_APB → 4 PUTs)     | ❌ EXCESS PUT | net -3 on deassert_count; asserts on LANE/CMN/INIT lack matching deasserts |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The function performs four reset_control_assert() (PUT) operations but only one reset_control_deassert() (GET), causing a net negative deassert_count (excess put) within the function – the asserts for LANE, CMN, INIT are unbalanced.
```
```
