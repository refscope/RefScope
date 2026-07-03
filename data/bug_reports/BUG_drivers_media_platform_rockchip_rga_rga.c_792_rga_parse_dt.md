# REAL BUG: drivers/media/platform/rockchip/rga/rga.c:792 rga_parse_dt()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L789 | error       | YES | NO | ❌ LEAK | hclk ERR - all three deasserted |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L747 | error       | NO (no deassert called yet) | N/A | ✅ | core_rst ERR |
| L753 | error       | NO | N/A | ✅ | axi_rst ERR |
| L759 | error       | NO | N/A | ✅ | ahb_rst ERR |
| L777 | error       | YES (all three deasserted) | NO | ❌ LEAK | sclk ERR - core, axi, ahb remain deasserted |
| L783 | error       | YES | NO | ❌ LEAK | aclk ERR - all three deasserted |
| L789 | error       | YES | NO | ❌ LEAK | hclk ERR - all three deasserted |
| L792 | success     | YES | NO (intentional) | ✅ | Successful probe keeps resets deasserted |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Four error paths after all three reset_control_deassert() calls return without reset_control_assert(), leaking deassert_count on core, axi, and ahb.
```
