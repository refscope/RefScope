# REAL BUG: drivers/mtd/nand/raw/brcmnand/brcmnand.c:3556 brcmnand_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

The missing `of_node_get()` in probe directly causes the excess put. This is a real driver bug.

## Full Response

```
| Line | Return Type | GET Done? (child loop) | PUT Done? (child loop) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L12  | error return | NO (before loop) | N/A | ✅ | No child node accessed |
| L16  | error return | NO (before loop) | N/A | ✅ | |
| L39  | error return | NO (before loop) | N/A | ✅ | Condition with soc_has_ops |
| L46  | error return (clk fail) | NO (before loop) | N/A | ✅ | |
| L50  | error return (EPROBE_DEFER) | NO (before loop) | N/A | ✅ | |
| L58  | goto err (revision_init fail) | NO (before loop) | N/A | ✅ | |
| L78  | goto err (nand-cache error) | NO (before loop) | N/A | ✅ | |
| L91  | goto err (flash-dma error) | NO (before loop) | N/A | ✅ | |
| L105 | goto err (dma mask error) | NO (before loop) | N/A | ✅ | |
| L117 | goto err (dma_desc alloc fail) | NO (before loop) | N/A | ✅ | |
| L124 | goto err (FLASH_DMA IRQ missing) | NO (before loop) | N/A | ✅ | |
| L133 | goto err (devm_request_irq fail) | NO (before loop) | N/A | ✅ | |
| L142 | goto err (edu_setup fail) | NO (before loop) | N/A | ✅ | |
| L189 | goto err (IRQ request fail) | NO (before loop) | N/A | ✅ | |
| L199 | goto err (devm_kzalloc fail in loop) | YES (child gotten by for-each) | YES (scoped cleanup) | ✅ | Scoped macro releases child on goto err |
| L208 | continue (of_property_read_u32 fail) | YES | YES (scoped cleanup at iteration end) | ✅ | |
| L216 | goto err (brcmnand_init_cs EPROBE_DEFER) | YES | YES (scoped cleanup) | ✅ | EPROBE_DEFER path still releases child |
| L219 | continue (brcmnand_init_cs other error) | YES | YES (scoped cleanup) | ✅ | |
| L227 | return 0 (host_list not empty) | NO (loop finished, all children released) | N/A (already released) | ✅ | Loop scope cleanup already released all references |
| L231 | goto err (no platform data) | NO (after loop) | N/A | ✅ | |
| L238 | goto err (devm_kzalloc fail, platform data) | NO | N/A | ✅ | |
| L248 | goto err (brcmnand_init_cs fail, platform) | NO | N/A | ✅ | |
| L255 | goto err (host_list empty check) | NO | N/A | ✅ | |
| L258 | return 0 (success) | NO | N/A | ✅ | |

**Analysis:**  
Within `brcmnand_probe()`, the `for_each_available_child_of_node_scoped` macro internally calls `of_get_next_available_child()` to obtain a reference on each child node, and the scoped cleanup automatically releases that reference on every exit from the loop iteration (continue, goto err, or loop end). Therefore all per-iteration gets are balanced, and the function itself has no local refcount imbalance.

**Root Cause of Warning:**  
The warning at line 3556 (elsewhere in the driver, likely in `brcmnand_remove()`) reports an *excess put* on the device_node’s kref. This occurs because `brcmnand_probe()` stores the child node pointer via `nand_set_flash_node(&host->chip, child)` **without calling `of_node_get(child)`** to take a long‑lived reference. The later cleanup code (e.g., `nand_release()` or an explicit `of_node_put()`) expects that refer
```
