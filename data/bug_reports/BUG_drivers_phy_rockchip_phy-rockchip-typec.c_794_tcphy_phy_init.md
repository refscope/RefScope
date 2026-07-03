# REAL BUG: drivers/phy/rockchip/phy-rockchip-typec.c:794 tcphy_phy_init()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L780 | return 0 (success) | YES | YES | YES | NO (held for lifetime) | NO | NO | ✅ (init pattern) | Resources held until phy teardown |

## Full Response

```
| Line | Return Type | GET Done? (tcphy_rst) | GET Done? (uphy_rst) | GET Done? (pipe_rst) | PUT Done? (tcphy_rst) | PUT Done? (uphy_rst) | PUT Done? (pipe_rst) | Balanced? | Notes |
|------|-------------|-----------------------|-----------------------|-----------------------|-----------------------|-----------------------|-----------------------|-----------|-------|
| L728 | return ret (error) | NO (before any deassert) | NO | NO | N/A | N/A | N/A | ✅ | core clk enable failed, no reset touched |
| L735 | goto err_clk_core (error) | NO | NO | NO | N/A | N/A | N/A | ✅ | ref clk enable failed, no reset touched |
| L779 | goto err_wait_pma (error, poll timeout) | YES (L739) | YES (L767) | YES (L776) | YES (assert at L781) | YES (assert at L780) | NO | ❌ LEAK | **pipe_rst deasserted but not asserted** – missing reset_control_assert(pipe_rst) |
| L780 | return 0 (success) | YES | YES | YES | NO (held for lifetime) | NO | NO | ✅ (init pattern) | Resources held until phy teardown |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_deassert(tcphy->pipe_rst)` at L776 is balanced by a `reset_control_assert(tcphy->pipe_rst)` only on the success path (held for device lifetime); the error path via `goto err_wait_pma` (L779) asserts `uphy_rst` and `tcphy_rst` but misses `pipe_rst`, leaking the deassert_count and causing inconsistent refcounting.
```
