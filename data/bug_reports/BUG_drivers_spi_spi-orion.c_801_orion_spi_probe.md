# REAL BUG: drivers/spi/spi-orion.c:801 orion_spi_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L760 `return 0` | success | N/A | N/A | ✅ | loop completed, all references balanced by iterator cleanup |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L653 | error (host==NULL) | N/A | N/A | ✅ | spi_alloc_host fail, no of_node acquired |
| L686 `goto out` | error (clk PTR_ERR) | N/A | N/A | ✅ | before loop |
| L689 `goto out` | error (axi_clk EPROBE_DEFER) | N/A | N/A | ✅ | before loop |
| L711 `goto out_rel_axi_clk` | error (spi->base IS_ERR) | N/A | N/A | ✅ | before loop |
| L801 `of_node_put(np); goto out_rel_axi_clk` | error (devm_ioremap fail) | YES (child node acquired by `for_each_available_child_of_node` iterator) | YES (explicit) + implicit `of_node_put` from `__free(device_node)` cleanup attribute of the scoped iterator | ❌ **Excess put** | The explicit `of_node_put(np)` is redundant because the scoped iterator automatically releases the reference when `np` goes out of scope (via goto). The double put causes a refcount excess. |
| L748 `goto out_rel_pm` | error (orion_spi_reset fail) | N/A | N/A | ✅ | loop already completed |
| L755 `goto out_rel_pm` | error (spi_register_controller fail) | N/A | N/A | ✅ | loop already completed |
| L760 `return 0` | success | N/A | N/A | ✅ | loop completed, all references balanced by iterator cleanup |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The scoped `for_each_available_child_of_node` iterator uses `__free(device_node)` which automatically releases the node reference. The explicit `of_node_put(np)` at L801 is an unnecessary second release, causing a refcount excess put.
```
