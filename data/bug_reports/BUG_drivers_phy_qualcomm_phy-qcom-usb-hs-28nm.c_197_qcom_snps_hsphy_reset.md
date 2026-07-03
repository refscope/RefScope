# REAL BUG: drivers/phy/qualcomm/phy-qcom-usb-hs-28nm.c:197 qcom_snps_hsphy_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| 197  | success return 0 | YES (deassert succeeded) | YES (assert succeeded) | ✅ | both succeeded, balanced. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 187  | assert error | NO (assert failed) | NO (assert failed) | ✅ | assert failed, no state change. |
| 193  | deassert error| NO (deassert failed) | YES (assert succeeded) | ❌ | assert (PUT) succeeded, deassert (GET) not done → excess put (refcount decremented but not restored). |
| 197  | success return 0 | YES (deassert succeeded) | YES (assert succeeded) | ✅ | both succeeded, balanced. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On deassert failure (line 193), the reset was already asserted and deassert_count decremented; the function returns without undoing the assert, leaving the counter unbalanced (excess put).
```
