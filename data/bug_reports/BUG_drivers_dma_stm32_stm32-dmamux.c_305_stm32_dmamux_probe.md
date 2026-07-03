# REAL BUG: drivers/dma/stm32/stm32-dmamux.c:305 stm32_dmamux_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L112→L121 (goto pm_disable) | error (router register fail) | YES (L90) | NO  | ❌ LEAK | cleanup only pm_runtime_disable & clk, no assert |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L13  | error (no node)        | NO  | N/A | ✅ | before rst get |
| L18  | error (count < 0)      | NO  | N/A | ✅ | |
| L24  | error (alloc fail)     | NO  | N/A | ✅ | |
| L34  | error (bad master)     | NO  | N/A | ✅ | |
| L51  | error (too many reqs)  | NO  | N/A | ✅ | |
| L67  | error (iomem)          | NO  | N/A | ✅ | |
| L73  | error (missing clk)    | NO  | N/A | ✅ | |
| L79  | error (clk enable fail)| NO  | N/A | ✅ | |
| L86 (goto err_clk) | error (rst EPROBE_DEFER) | NO | N/A | ✅ | deassert not called |
| L114 | success                | YES (L90) | NO  | ❌ LEAK | missing reset_control_assert |
| L112→L121 (goto pm_disable) | error (router register fail) | YES (L90) | NO  | ❌ LEAK | cleanup only pm_runtime_disable & clk, no assert |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After `reset_control_deassert` (L90) the deassert_count is incremented, but neither the success return (L114) nor the error path via `pm_disable`/`err_clk` (L112→L121) calls `reset_control_assert` to decrement it, leaking the reference.
```
