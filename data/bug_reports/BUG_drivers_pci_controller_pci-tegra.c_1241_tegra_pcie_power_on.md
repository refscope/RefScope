# REAL BUG: drivers/pci/controller/pci-tegra.c:1241 tegra_pcie_power_on()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L1223 | goto err (disable_cml_clk) | NO | YES (L1182) | ❌ imbalance | same |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1228 | success     | YES (L1226) | YES (L1182) | ✅ | net balanced |
| L1197 | goto err (regulator_disable) | NO (no deassert) | YES (L1182) | ❌ imbalance | unconditional assert before goto, no deassert |
| L1202 | goto err (powergate) | NO | YES (L1182) | ❌ imbalance | same |
| L1209 | goto err (powergate) | NO | YES (L1182) | ❌ imbalance | same |
| L1216 | goto err (disable_afi_clk) | NO | YES (L1182) | ❌ imbalance | same |
| L1223 | goto err (disable_cml_clk) | NO | YES (L1182) | ❌ imbalance | same |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
reset_control_assert (PUT) is called unconditionally at top; error paths never call reset_control_deassert (GET) to balance it, leaving deassert_count underflowed.
```
