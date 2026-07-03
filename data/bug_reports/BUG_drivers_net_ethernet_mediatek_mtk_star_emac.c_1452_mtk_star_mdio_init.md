# REAL BUG: drivers/net/ethernet/mediatek/mtk_star_emac.c:1452 mtk_star_mdio_init()

**Confidence**: HIGH | **Counter**: `mdio_node->kobj.kref.refcount.refs.counter`

## Reasoning

| L1449→label | success or error after `devm_of_mdiobus_register` | YES | YES (unconditional) | ❌ | The devm_of_mdiobus_register function takes ownership of the node reference; this caller’s of_node_put is an excess put, leading to premature free and double release on device removal. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1431 | error (early return, `mdio_node == NULL`) | NO (NULL, get not attempted) | N/A | ✅ | No reference taken. |
| L1437 | goto out_put_node (on `priv->mii` allocation failure) | YES | YES | ✅ | `of_node_put` called at label. This path alone is balanced. |
| L1449→label | success or error after `devm_of_mdiobus_register` | YES | YES (unconditional) | ❌ | The devm_of_mdiobus_register function takes ownership of the node reference; this caller’s of_node_put is an excess put, leading to premature free and double release on device removal. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`devm_of_mdiobus_register` consumes the `device_node` reference, making the subsequent unconditional `of_node_put` an excess put. The driver must not release the node on the success path, only on error before the devm hook is installed.
```
