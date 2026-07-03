# REAL BUG: drivers/pci/controller/dwc/pcie-stm32-ep.c:223 stm32_add_pcie_ep()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| ~L235 (success return) | success | YES | NO (intentional) | ✅ | device stays deasserted; assert expected in remove/shutdown |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L199 (regmap_update error) | error (before GET) | NO | N/A  | ✅ | `reset_control_deassert` not called |
| **L223 (dw_pcie_ep_init error)** | error | **YES** | **NO**  | **❌ LEAK** | `reset_control_deassert` executed at L205; no `reset_control_assert` on this path |
| ~L228 (enable_resources error) | error | YES | NO  | ❌ LEAK | same, no assert on error |
| ~L235 (success return) | success | YES | NO (intentional) | ✅ | device stays deasserted; assert expected in remove/shutdown |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_deassert` at L205 increments deassert_count, but the two error return paths after it (ep_init failure at L223 and enable_resources failure) leak the count by not calling `reset_control_assert`.
```
