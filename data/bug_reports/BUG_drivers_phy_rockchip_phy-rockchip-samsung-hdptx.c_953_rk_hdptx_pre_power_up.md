# REAL BUG: drivers/phy/rockchip/phy-rockchip-samsung-hdptx.c:953 rk_hdptx_pre_power_up()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

4. goto out? No gotos; single linear path.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~951 (end of function) | void return | For RST_APB: YES (deassert at line ~945). For RST_LANE, RST_CMN, RST_INIT: NO deassert in this function. | RST_APB: YES (assert at line ~943). RST_LANE, RST_CMN, RST_INIT: YES (assert calls at lines ~946, ~947, ~948). | ❌ For RST_LANE / RST_CMN / RST_INIT: PUT without a prior GET in this function. Smatch reports **excess put** at line 953, indicating the deassert_count was already zero when one of these asserts was called—underflow. | The warning points to an actual refcount underflow. The function unconditionally calls reset_control_assert on three resets that have no balancing deassert, and at least one is called while the counter is zero, which is a real refcount violation. |

**Pre‑verdict checklist answers:**
1. “Held for device lifetime”? Not applicable — the function runs during pre‑power‑up, not only on successful probe; no deasserts are provided for these resets.
2. “Ownership transferred”? No evidence of a cleanup mechanism that would make the unbalanced assert safe; default is no transfer → real bug.
3. Unconditional GET? The only GET (deassert) is for RST_APB; the three warned‑about resets have **zero GETs** in this function. The PUTs are unconditional, so every execution hits them. If the counter is already zero, underflow occurs.
4. goto out? No gotos; single linear path.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`rk_hdptx_pre_power_up` calls `reset_control_assert` on RST_LANE, RST_CMN, and RST_INIT without any matching `reset_control_deassert` in the function; smatch’s “excess put” on line 953 directly shows a counter underflow (deassert_count was zero at the time of the assert), confirming a real refcount imbalance.
```
