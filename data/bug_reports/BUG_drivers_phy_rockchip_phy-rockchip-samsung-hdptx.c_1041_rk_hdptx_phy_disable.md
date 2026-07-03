# REAL BUG: drivers/phy/rockchip/phy-rockchip-samsung-hdptx.c:1041 rk_hdptx_phy_disable()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L1042 (function end) | void return | NO (no deassert for RST_INIT) | YES (assert at L1039) | ❌ EXCESS PUT | assert called without prior deassert — deassert_count underflow |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1042 (function end) | void return | NO (no deassert for RST_INIT) | YES (assert at L1039) | ❌ EXCESS PUT | assert called without prior deassert — deassert_count underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
`reset_control_assert()` for RST_INIT (line 1039) is called without any preceding `reset_control_deassert()` for the same reset control; this causes an excess put (negative refcount) on the internal deassert counter.
```
