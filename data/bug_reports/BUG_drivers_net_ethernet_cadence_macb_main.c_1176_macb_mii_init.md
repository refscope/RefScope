# REAL BUG: drivers/net/ethernet/cadence/macb_main.c:1176 macb_mii_init()

**Confidence**: MEDIUM | **Counter**: `mdio_np->kobj.kref.refcount.refs.counter`

## Reasoning

_probe(bp->dev)` fails, the code jumps to `err_out_unregister_bus`, which eventually reaches `err_out` and calls `of_node_put(mdio_np)`. This is a double put because the reference was already handed over. Smatch detects the resulting refcount underflow as “refcount excess put” at line 1176.

## Full Response

```
## Path Table

| Line (approx) | Return Type         | GET Done? | PUT Done? | Balanced? | Notes |
|---------------|---------------------|-----------|-----------|-----------|-------|
| ~1134         | early return (success) | NO (mdio_np NULL) | NO  | ✅ | No reference held. |
| ~1146         | error goto `err_out` (mdiobus_alloc fail) | YES (mdio_np non‑NULL) | YES (via `err_out`) | ✅ | Still own initial reference; put is correct. |
| ~1156         | error goto `err_out_free_mdiobus` (macb_mdiobus_register fail) | YES (mdio_np non‑NULL) | YES (via `err_out` after `mdiobus_free`) | ✅ | Registration failed, ownership NOT transferred; put is correct. |
| ~1166         | error goto `err_out_unregister_bus` (macb_mii_probe fail after registration succeeded) | YES (mdio_np non‑NULL) | YES (via `err_out` after unregister/free) | ❌ **EXCESS PUT** | `macb_mdiobus_register` succeeded → ownership of the node’s reference was transferred to the MDIO bus; the caller must NOT call `of_node_put` here. Doing so causes a double release (refcount underflow). |
| ~1172         | return 0 (success)  | YES (mdio_np non‑NULL) | NO  | ✅ | Ownership transferred; put will be done during bus teardown. |

## Analysis

- **GET contract**: `of_get_child_by_name` returns a node with a “must-release” reference (NULL is safe, no reference).  
- **Ownership transfer**: After a successful call to `macb_mdiobus_register(bp, mdio_np)`, the node reference is typically stored in `bp->mii_bus->dev.of_node` without an additional `of_node_get`. The caller’s reference is thereby **consumed/transferred**. The caller must **not** release it on error paths that occur *after* that registration succeeds.  
- **Path at issue**: When `macb_mii_probe(bp->dev)` fails, the code jumps to `err_out_unregister_bus`, which eventually reaches `err_out` and calls `of_node_put(mdio_np)`. This is a double put because the reference was already handed over. Smatch detects the resulting refcount underflow as “refcount excess put” at line 1176.

## PRE-VERDICT CHECKLIST

1. **“Held for device lifetime” error paths?** YES – the error path after successful registration still puts, causing excess put.  
2. **Ownership transfer?** YES – `macb_mdiobus_register` stores the node; the cleanup (if needed) is done during bus teardown, not by this function on error.  
3. **Unconditional GET?** The get was conditional (NULL possible), but in the analysed path `mdio_np` was != NULL.  
4. **goto between GET and PUT?** The `goto err_out_unregister_bus` traverses labels that lead to `err_out` and the put, but the put should not happen in this scenario.  

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`macb_mdiobus_register` consumes the node reference; the error path after its success incorrectly calls `of_node_put`, causing refcount underflow (excess put).
```
