# REAL BUG: drivers/clocksource/timer-cadence-ttc.c:549 ttc_timer_probe()

**Confidence**: MEDIUM | **Counter**: `$->core.ref.refcount.refs.counter`

## Reasoning

| L539 | return 0      | YES         | YES         | NO               | ❌ LEAK | **Success path – neither clock ref released** |

## Full Response

```
| Line | Return Type | clk_cs GET? | clk_ce GET? | PUT Done? | Balanced? | Notes |
|------|-------------|-------------|-------------|-----------|-----------|-------|
| L490 | return 0 (early) | NO          | NO          | N/A       | ✅        | Before any gets |
| L498 | return PTR_ERR | NO          | NO          | N/A       | ✅        | Before any gets |
| L504 | return -EINVAL | NO          | NO          | N/A       | ✅        | Before any gets |
| L519 | return PTR_ERR(clk_cs) | NO (IS_ERR) | NO          | N/A       | ✅        | First get failed; no ref held |
| L529 | goto put_clk_cs | YES         | NO (IS_ERR) | clk_put(clk_cs) | ✅        | Second get failed; release first |
| L533 | goto put_clk_ce | YES         | YES         | clk_put(ce), then cs | ✅   | ttc_setup_clocksource failed |
| L537 | goto put_clk_ce | YES         | YES         | both puts           | ✅   | ttc_setup_clockevent failed |
| L539 | return 0      | YES         | YES         | NO               | ❌ LEAK | **Success path – neither clock ref released** |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`of_clk_get` acquires references for both clock-controller and clock-event clocks. The success path (return 0) releases neither; no ownership transfer or deferred cleanup is visible, so both refcounts are leaked.
```
