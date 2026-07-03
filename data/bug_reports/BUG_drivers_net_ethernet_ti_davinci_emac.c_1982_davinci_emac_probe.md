# REAL BUG: drivers/net/ethernet/ti/davinci_emac.c:1982 davinci_emac_probe()

**Confidence**: MEDIUM | **Counter**: `priv->phy_node->kobj.kref.refcount.refs.counter`

## Reasoning

ecrement a kref that was never incremented, causing an underflow (excess put). Because the warning is an actual “excess put” detected on a specific kernel, and the contract confirms the get is conditional, it is highly likely that such a path exists and is reachable. Therefore the bug is **real**.

## Full Response

```
| Line | Return Type | GET Done? (phy_node) | PUT Done? | Balanced? | Notes |
|------|-------------|----------------------|-----------|-----------|-------|
| 1808 | error       | NO (before any get)  | NO        | ✅        | early exit, no phy_node |
| 1817 | error       | NO (no pdata)        | NO        | ✅        | alloc_etherdev fails |
| 1834 | goto err_free_netdev | NO (pdata==NULL) | NO   | ✅        | pdata allocation failed, no phy reference |
| 1847 | goto no_pdata | UNCERTAIN (davinci_emac_of_get_pdata may or may not have taken ref) | YES (of_node_put) | ❓ (excess if GET=NO and phy_node!=NULL) | remap error |
| 1855 | goto no_pdata | UNCERTAIN               | YES        | ❓         | ctrl_base error |
| 1884 | goto no_pdata | UNCERTAIN               | YES        | ❓         | DMA create error |
| 1891 | goto err_free_dma→no_pdata | UNCERTAIN | YES | ❓ | txchan error |
| 1898 | goto err_free_txchan→no_pdata| UNCERTAIN| YES | ❓ | rxchan error |
| 1909 | goto err_free_rxchan→no_pdata| UNCERTAIN| YES | ❓ | platform_get_irq error |
| 1937 | goto err_napi_del→no_pdata  | UNCERTAIN | YES | ❓ | pm_runtime error |
| 1945 | goto err_napi_del→no_pdata  | UNCERTAIN | YES | ❓ | register_netdev error |
| 1954 | success       | YES (if phy present)  | NO (lifetime hold) | ✅ | reference kept for driver lifetime |

[NEED_SOURCE] davinci_emac_of_get_pdata

**Analysis**  
The warning tags an **excess put** on `priv->phy_node` at the `no_pdata` label (line 1982). The `of_node_put()` is called unconditionally on all error paths after a successful `davinci_emac_of_get_pdata()` (i.e., `pdata != NULL`). However, the **Get contract for that function says it is “conditional_on_path”** and that it optionally calls `of_node_get()`. This means there exist code paths inside `davinci_emac_of_get_pdata()` where it may set `priv->phy_node` to a non‑NULL value **without** taking a reference. On those paths the subsequent `of_node_put()` will decrement a kref that was never incremented, causing an underflow (excess put). Because the warning is an actual “excess put” detected on a specific kernel, and the contract confirms the get is conditional, it is highly likely that such a path exists and is reachable. Therefore the bug is **real**.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`davinci_emac_of_get_pdata` can leave `priv->phy_node` non‑NULL without a get; error paths unconditionally `of_node_put()` it, risking underflow.
```
