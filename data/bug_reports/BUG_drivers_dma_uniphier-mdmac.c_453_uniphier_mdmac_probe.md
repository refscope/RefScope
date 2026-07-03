# REAL BUG: drivers/dma/uniphier-mdmac.c:453 uniphier_mdmac_probe()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

53) those references are never released, because `disable_clk` only disables the clock and `unregister_dmac` only handles the registration‑time extra references. The leak on L53 remains even though `dma_async_device_unregister()` is called – it does not drop the per‑channel init references.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L10  | error (nr_chans < 0)                    | NO (before any init) | N/A  | ✅ | |
| L14  | error (dma_set_mask fail)               | NO  | N/A  | ✅ | |
| L19  | error (devm_kzalloc fail)               | NO  | N/A  | ✅ | |
| L23  | error (ioremap fail)                    | NO  | N/A  | ✅ | |
| L28  | error (clk_get fail)                    | NO  | N/A  | ✅ | |
| L33  | error (clk_prepare_enable fail)         | NO  | N/A  | ✅ | |
| L43  | error (for-loop → goto disable_clk)     | YES (all previously‑initialised channels) | NO | ❌ LEAK | No release of channel refcounts set by `uniphier_mdmac_chan_init()` |
| L48  | error (`dma_async_device_register` fail → goto disable_clk) | YES (all channels initialised) | NO | ❌ LEAK | No channel cleanup after failed register |
| L53  | error (`of_dma_controller_register` fail → goto unregister_dmac) | YES (all channels, + register refs) | YES (unregister called) | ❌ LEAK | `dma_async_device_unregister()` releases register refs, but channel‑init refs (kref=1) are still not freed |
| L57  | success (return 0)                      | YES (all channels, register) | NO (held for device lifetime) | ✅ | Channels cleaned up in driver’s `remove()` callback |

**Explanation of GET**: The `uniphier_mdmac_chan_init()` function creates a DMA channel and sets its kref to 1 (a “get” on the channel’s life‑cycle reference). For every channel that succeeds before an error, the driver holds that reference. On the error paths after the loop (L43, L48, L53) those references are never released, because `disable_clk` only disables the clock and `unregister_dmac` only handles the registration‑time extra references. The leak on L53 remains even though `dma_async_device_unregister()` is called – it does not drop the per‑channel init references.

## PRE-VERDICT CHECKLIST

1. **“Held for device lifetime”?** – Only the **success** return (L57) relies on `remove()`. All error paths return before binding → `remove()` never fires → they **must** explicitly release the channel references. **FAIL** → LEAK.
2. **“Ownership transferred”?** – No. The channels are never added to any list that provides automatic cleanup; the driver is the sole owner. **FAIL** → no implicit transfer.
3. **Unconditional GET?** – `uniphier_mdmac_chan_init()` unconditionally sets the channel kref to 1 on success. After any successful `chan_init()`, the reference is held. **FAIL** → no guard on the error paths.
4. **goto out between GET and PUT?** – `goto disable_clk` (L43, L48) does `clk_disable_unprepare` only; `goto unregister_dmac` (L53) calls `dma_async_device_unregister` but still no channel‑ref release. **FAIL** → explicit leak on both `goto` targets.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`uniphier_mdmac_chan_init()` unconditionally takes a reference on each DMA channel. On the error paths after the for‑loop (goto disable_clk
```
