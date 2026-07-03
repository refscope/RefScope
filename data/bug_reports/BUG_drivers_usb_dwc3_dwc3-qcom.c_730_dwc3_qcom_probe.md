# REAL BUG: drivers/usb/dwc3/dwc3-qcom.c:730 dwc3_qcom_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L723 | success (return 0) | YES | NO | ✅ (deliberate) | device held for lifetime; assert in remove() |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L623 | error (-ENOMEM) | NO (before GET) | N/A | ✅ | |
| L629-630 | error (IS_ERR guard) | NO (before deassert) | N/A | ✅ | |
| L635 | error (clk get fail) | NO | N/A | ✅ | |
| L641 | error (assert fail) | NO (assert is PUT, not GET; GET later) | N/A | ✅ | |
| L649 | error (deassert fail) | NO (conditional GET, error means no inc) | N/A | ✅ | |
| L654 | error (clk enable fail) | YES (deassert succeeded) | NO | ❌ LEAK | |
| L659-660 (goto clk_disable) | error (resource not found) | YES | NO | ❌ LEAK | clk_disable has no reset_control_assert |
| L668-669 (goto clk_disable) | error (qscratch map fail) | YES | NO | ❌ LEAK | |
| L674-675 (goto clk_disable) | error (irq setup fail) | YES | NO | ❌ LEAK | |
| L711 (goto clk_disable) | error (dwc3 core probe fail) | YES | NO | ❌ LEAK | |
| L716 (goto remove_core) | error (interconnect init fail) | YES | NO | ❌ LEAK | remove_core → clk_disable, no assert |
| L723 | success (return 0) | YES | NO | ✅ (deliberate) | device held for lifetime; assert in remove() |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
```
