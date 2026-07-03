# REAL BUG: drivers/mmc/host/davinci_mmc.c:1337 davinci_mmcsd_probe()

**Confidence**: HIGH | **Counter**: `$->dma_rx->device.ref.refcount.refs.counter`

## Reasoning

| ~L142: success | return 0 | YES (if dma) | NO (held for device lifetime, remove() will release) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L12: no memory resource | return -ENODEV | NO (before get) | N/A | ✅ | early return |
| ~L15: no IRQ | return irq | NO | N/A | ✅ | |
| ~L21: devm_request_mem_region fails | return -EBUSY | NO | N/A | ✅ | |
| ~L25: devm_mmc_alloc_host fails | return -ENOMEM | NO | N/A | ✅ | |
| ~L33: devm_ioremap fails | return -ENOMEM | NO | N/A | ✅ | |
| ~L37: devm_clk_get fails | return PTR_ERR | NO | N/A | ✅ | |
| ~L41: clk_prepare_enable fails | return ret | NO | N/A | ✅ | |
| ~L51: mmc_of_parse fails → goto parse_fail | goto parse_fail | NO (dma not yet acquired) | N/A | ✅ | parse_fail label; no ref held |
| ~L58: mmc_davinci_parse_pdata fails → goto parse_fail | goto parse_fail | NO | N/A | ✅ | same |
| **~L73: davinci_acquire_dma_channels returns -EPROBE_DEFER → goto dma_probe_defer** | **goto dma_probe_defer** | **YES (ref taken before defer)** | **NO (skips release)** | **❌ LEAK** | **dma_probe_defer only does clk_disable_unprepare; no davinci_release_dma_channels** |
| ~L75: other dma error → set use_dma=0, continue | continue | NO (function must clean up on error) | N/A | ✅ | no goto |
| ~L111: cpufreq register fails → goto cpu_freq_fail | goto cpu_freq_fail | YES (if dma acquired) | YES (davinci_release_dma_channels called) | ✅ | |
| ~L116: mmc_add_host fails → goto mmc_add_host_fail | goto mmc_add_host_fail | YES (if dma) | YES (fall through to cpu_freq_fail → release) | ✅ | |
| ~L121: request_irq fails → goto request_irq_fail | goto request_irq_fail | YES (if dma) | YES (mmc_remove_host → fall through to cpu_freq_fail release) | ✅ | |
| ~L142: success | return 0 | YES (if dma) | NO (held for device lifetime, remove() will release) | ✅ | |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**

`davinci_acquire_dma_channels` presumably increments a kref on the DMA device when it starts its work. On `-EPROBE_DEFER` the code jumps to `dma_probe_defer`, which skips `davinci_release_dma_channels` entirely, leaking the reference. The other error paths that go through `cpu_freq_fail` properly call the release function.
```
