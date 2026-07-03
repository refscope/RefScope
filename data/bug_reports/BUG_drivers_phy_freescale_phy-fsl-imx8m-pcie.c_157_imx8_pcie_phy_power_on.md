# REAL BUG: drivers/phy/freescale/phy-fsl-imx8m-pcie.c:157 imx8_pcie_phy_power_on()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

- **Probe-get/Remove-put?** Not applicable, but analogous: resources held until device removal only cover the success return.

## Full Response

```
| Line | Return Type | GET Done? (deassert) | PUT Done? (assert) | Balanced? | Notes |
|------|-------------|----------------------|-------------------|-----------|-------|
| ~175 (ret == 0)  | success             | YES (perst + reset) | NO                          | ⚠️ (cross-function) | Power_off will call assert, balancing the get |
| ~175 (ret < 0, e.g. poll timeout) | error               | YES (perst + reset) | NO                          | ❌ LEAK             | No unwind on failure; power_off will NOT be called, causing permanent underflow of deassert_count |

**Analysis:**
- The GET is performed unconditionally by the two `reset_control_deassert()` calls (lines for perst and reset).
- The function has only one return point (final `return ret;`), but `ret` can be 0 (success) or negative (poll failure via `readl_poll_timeout`).
- On **success** the consumer will later call `phy_power_off()`, which is expected to call `reset_control_assert()` on the same lines, so the refcount is balanced across the power_on/power_off pair. Smatch cannot see this cross-function pairing, so its warning for the success path would be a false positive.
- On **error** (`ret < 0`) the PHY power-on has failed. The standard driver model expects that after a failed `phy_power_on()` the consumer will NOT call `phy_power_off()`. Thus the deassert_count is never decremented, leaving the reset control in a permanently elevated state. The function does not perform any rollback of the deasserts before returning the error.

Therefore, the error path (poll timeout) leaks the refcount.

**FP Checklist:**
- **GET=YES, PUT=NO on error path, and no IS_ERR guard → REAL_BUG.**
- **Ownership transfer?** On error, the PHY is not fully powered, no ownership is transferred to the consumer; the reset control must be explicitly released.
- **Probe-get/Remove-put?** Not applicable, but analogous: resources held until device removal only cover the success return.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On error path (poll timeout), the refcount acquired by `reset_control_deassert()` at line 157 (and the perst deassert) is never released because `phy_power_off()` will not be invoked. The function must assert the reset controls before returning error.
```
