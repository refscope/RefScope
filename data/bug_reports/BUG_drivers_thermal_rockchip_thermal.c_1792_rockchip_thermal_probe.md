# REAL BUG: drivers/thermal/rockchip_thermal.c:1792 rockchip_thermal_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1792 | success (return 0)           | ❌ NO (stored child pointer lacks of_node_get) | N/A | ❌ UNBALANCED | Same – probe stores child of_node without taking a reference |

## Full Response

```
| Line | Return Type | GET Done? (of_node ref for stored child) | PUT Done? | Balanced? | Notes |
|------|-------------|------------------------------------------|-----------|-----------|-------|
| L1703 | error (irq < 0) | N/A (before any child loop) | N/A | ✅ | no child involvement |
| L1708 | error (alloc fail) | N/A | N/A | ✅ | |
| L1714 | error (no chip) | N/A | N/A | ✅ | |
| L1719 | error (alloc fail) | N/A | N/A | ✅ | |
| L1723 | error (IS_ERR)   | N/A | N/A | ✅ | |
| L1727 | error (reset fail) | N/A | N/A | ✅ | |
| L1732 | error (clk fail)   | N/A | N/A | ✅ | |
| L1737 | error (pclk fail)  | N/A | N/A | ✅ | |
| L1744 | error (config fail) | N/A | N/A | ✅ | before for_each_available_child_of_node |
| L1767 | error (sensor register fail) | ❌ NO (stored child pointer lacks of_node_get) | N/A | ❌ UNBALANCED | Missing get → future of_node_put in remove will be excess |
| L1776 | error (irq request fail)     | ❌ NO (stored child pointer lacks of_node_get) | N/A | ❌ UNBALANCED | Same |
| L1792 | success (return 0)           | ❌ NO (stored child pointer lacks of_node_get) | N/A | ❌ UNBALANCED | Same – probe stores child of_node without taking a reference |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Probe stores `child` (device_node) into `thermal->sensors[chn].of_node` inside the `for_each_available_child_of_node` loop without an explicit `of_node_get(child)`. The loop’s macro implicitly releases the reference it acquired on each child, leaving the stored pointer with no held reference. Later cleanup (e.g., in the remove function) will call `of_node_put` on this pointer, resulting in an **excess put** because the probe never took the corresponding reference. This is a classic missing `of_node_get` bug that leads to the reported kref counter imbalance.
```
