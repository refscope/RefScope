# REAL BUG: drivers/net/ethernet/spacemit/k1_emac.c:1014 emac_mdio_init()

**Confidence**: HIGH | **Counter**: `mii_np->kobj.kref.refcount.refs.counter`

## Reasoning

| L1015 | error (ret!=0, `mii_np` non-NULL) | YES | YES (by `devm_of_mdiobus_register` error path) + YES (caller's `of_node_put`) | ❌ EXCESS PUT | `devm_of_mdiobus_register` already releases the node’s reference on failure, making the caller’s `of_node_put` a double put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L996 | error (-ENOMEM) | NO (before get) | NO | ✅ | No call to `of_get_available_child_by_name`, no ref held. |
| L1015 | success (ret==0, `mii_np` non-NULL) | YES (`of_get_available_child_by_name` returned valid node) | YES (caller's `of_node_put`) + `devm_of_mdiobus_register` internally holds reference | ✅ | Caller releases its own reference; bus holds its reference. |
| L1015 | error (ret!=0, `mii_np` non-NULL) | YES | YES (by `devm_of_mdiobus_register` error path) + YES (caller's `of_node_put`) | ❌ EXCESS PUT | `devm_of_mdiobus_register` already releases the node’s reference on failure, making the caller’s `of_node_put` a double put. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`emac_mdio_init` unconditionally calls `of_node_put(mii_np)` after `devm_of_mdiobus_register`. On failure, the devm registration function already calls `of_node_put` internally (standard `of_mdiobus_register` error path), causing a refcount underflow and triggering the “excess put” warning.
```
