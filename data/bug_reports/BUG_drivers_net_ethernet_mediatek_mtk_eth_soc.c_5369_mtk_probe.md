# REAL BUG: drivers/net/ethernet/mediatek/mtk_eth_soc.c:5369 mtk_probe()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L5369 (final return err) | error | YES | NO | ❌ LEAK | all error paths converge here, no put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L5104 | error (-ENOMEM) | NO (before get) | N/A | ✅ | alloc fail |
| L5112 | error (PTR_ERR) | NO | N/A | ✅ | ioremap fail |
| L5124 | error (-EINVAL) | NO | N/A | ✅ | DMA mask fail |
| L5143 | error (PTR_ERR) | NO | N/A | ✅ | ethsys fail |
| L5151 | error (PTR_ERR) | NO | N/A | ✅ | infra fail |
| L5166 | error (sgmii init) | YES (of_dma_is_coherent) | NO | ❌ LEAK | get at L5155, no put before return |
| goto err_destroy_sgmii (required_pctl) | error | YES | NO | ❌ LEAK | label only calls sgmii_destroy, no put |
| goto err_destroy_sgmii (netsys res fail) | error | YES | NO | ❌ LEAK | same label |
| goto err_destroy_sgmii (netsys sram fail) | error | YES | NO | ❌ LEAK | same label |
| goto err_wed_exit (mtk_get_irqs) | error | YES | NO | ❌ LEAK | chain → err_destroy_sgmii, no put |
| goto err_wed_exit (clk defer) | error | YES | NO | ❌ LEAK | chain → err_destroy_sgmii, no put |
| goto err_wed_exit (clk missing) | error | YES | NO | ❌ LEAK | chain → err_destroy_sgmii, no put |
| goto err_wed_exit (mtk_hw_init) | error | YES | NO | ❌ LEAK | chain → err_destroy_sgmii, no put |
| goto err_deinit_hw (mtk_add_mac fail) | error | YES | NO | ❌ LEAK | puts mac_np but not of_node from dma |
| goto err_free_dev (irq fail) | error | YES | NO | ❌ LEAK | chain → err_deinit_hw …, no put |
| goto err_free_dev (mdio fail) | error | YES | NO | ❌ LEAK | same chain, no put |
| goto err_deinit_ppe (ppe fail) | error | YES | NO | ❌ LEAK | chain → err_free_dev …, no put |
| goto err_deinit_ppe (register fail) | error | YES | NO | ❌ LEAK | same chain, no put |
| goto err_unreg_netdev (dummy alloc fail) | error | YES | NO | ❌ LEAK | chain …, no put |
| return 0 (success) | success | YES | NO | ❌ LEAK | no of_node_put on success |
| L5369 (final return err) | error | YES | NO | ❌ LEAK | all error paths converge here, no put |

VERDICT: REAL_BUG  
CONFIDENCE: LOW  

The unconditional GET from `of_dma_is_coherent` at line 5155 acquires a reference that is never released on any subsequent return path (error or success). No ownership transfer is documented, and none of the cleanup labels (`err_destroy_sgmii` etc.) call `of_node_put`. Confidence is LOW because the `of_dma_is_coherent` contract may not accurately reflect its net reference effect (the function typically puts internally), but using the contract as ground truth forces a leak conclusion.
```
