# REAL BUG: drivers/phy/qualcomm/phy-qcom-usb-ss.c:87 qcom_ssphy_do_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L83  | error       | YES (deassert_com succeeded) | NO | ❌ LEAK | Missing assert(priv->reset_com) to undo deassert. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L63  | error       | NO (no deassert yet) | N/A | ✅ | Before any deassert get. |
| L69  | error       | NO (no deassert yet) | N/A | ✅ | Before any deassert get. |
| L77  | error       | NO (deassert_com failed) | N/A | ✅ | Conditional GET; no ref held. |
| L83  | error       | YES (deassert_com succeeded) | NO | ❌ LEAK | Missing assert(priv->reset_com) to undo deassert. |
| L87  | success     | YES (both) | NO (by design) | ✅ | Ownership retained; caller will assert later. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On error path at L83, `reset_control_deassert(reset_com)` succeeded but `reset_control_deassert(reset_phy)` failed; the function returns without calling `reset_control_assert(reset_com)` to undo the deassert, leaking the `deassert_count` for `reset_com`.
```
