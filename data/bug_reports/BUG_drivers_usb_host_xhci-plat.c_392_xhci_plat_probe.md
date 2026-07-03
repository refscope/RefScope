# REAL BUG: drivers/usb/host/xhci-plat.c:392 xhci_plat_probe()

**Confidence**: LOW | **Counter**: `$->deassert_count.counter`

## Reasoning

i_plat_remove`) indicates smatch either cannot find the corresponding `reset_control_assert` in the remove function or sees an imbalance. Without the remove() source, we cannot confirm if the assert is missing. If remove() lacks `reset_control_assert`, it's a leak; otherwise it's a false positive.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L163 | early (usb_disabled) | NO (before deassert) | N/A | ✅ | return -ENODEV |
| L167 | early (irq < 0) | NO | N/A | ✅ | return irq |
| L173 | early (dma_set_mask) | NO | N/A | ✅ | return ret |
| L191 | disable_runtime (hcd NULL) | NO | N/A | ✅ | goto disable_runtime, no get |
| L196 | put_hcd (hcd->regs IS_ERR) | NO | N/A | ✅ | before deassert |
| L207 | put_hcd (reg_clk error) | NO | N/A | ✅ | before deassert |
| L213 | put_hcd (clk error) | NO | N/A | ✅ | before deassert |
| L219 | put_hcd (xhci->reset error) | NO | N/A | ✅ | reset get failed → no deassert |
| L224 | put_hcd (deassert error) | NO (get failed) | N/A | ✅ | ret != 0, no ref held |
| L228 | err_reset (clk_prepare_enable reg_clk fail) | YES | YES | ✅ | err_reset calls assert |
| L232 | disable_reg_clk (clk_prepare_enable clk fail) | YES | YES | ✅ | path: disable_reg_clk → err_reset |
| L248 | disable_clk (EPROBE_DEFER) | YES | YES | ✅ | disable_clk → disable_reg_clk → err_reset |
| L253 | disable_clk (usb_phy_init fail) | YES | YES | ✅ | same |
| L268 | disable_usb_phy (usb_add_hcd fail) | YES | YES | ✅ | disable_usb_phy → disable_clk → ... → err_reset |
| L275 | dealloc_usb2_hcd (shared_hcd alloc fail) | YES | YES | ✅ | dealloc_usb2_hcd → disable_usb_phy → ... → err_reset |
| L287 | put_usb3_hcd (shared_hcd add fail) | YES | YES | ✅ | put_usb3_hcd → dealloc_usb2_hcd → ... → err_reset |
| L308 | success (return 0) | YES | NO | ⚠️ | held for device lifetime; must be released in remove() |

[NEED_SOURCE] xhci_plat_remove

**Analysis**: All probe error paths after `reset_control_deassert` call `reset_control_assert`. The success path intentionally leaves deassert held, relying on the driver's remove function to release it. The warning at line 392 (likely inside `xhci_plat_remove`) indicates smatch either cannot find the corresponding `reset_control_assert` in the remove function or sees an imbalance. Without the remove() source, we cannot confirm if the assert is missing. If remove() lacks `reset_control_assert`, it's a leak; otherwise it's a false positive.

VERDICT: REAL_BUG
CONFIDENCE: LOW
Pending verification of xhci_plat_remove() — if that function does not call reset_control_assert, the deassert ref held in probe success is never released.
```
