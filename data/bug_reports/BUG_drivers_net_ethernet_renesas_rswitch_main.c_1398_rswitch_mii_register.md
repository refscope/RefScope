# REAL BUG: drivers/net/ethernet/renesas/rswitch_main.c:1398 rswitch_mii_register()

**Confidence**: MEDIUM | **Counter**: `mdio_np->kobj.kref.refcount.refs.counter`

## Reasoning

efcount excess put” on the `mdio_np` kref at line 1398. On the error path, `of_mdiobus_register()` likely consumes (or internally puts) the reference on failure, so the caller’s subsequent `of_node_put(mdio_np)` is an extra put that drives the counter below zero.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 1372 | error: `return -ENOMEM;` | NO (before get) | N/A | ✅ | mdiobus_alloc fail, no ref held |
| 1390 | get: `mdio_np = of_get_child_by_name(...)` | YES (if non-NULL) | - | - | acquires ref; if NULL, get is no‑op |
| 1393–1395 (error path) | err < 0 → `mdiobus_free(mii_bus); goto out;` → L1398 `of_node_put(mdio_np); return err;` | YES (if mdio_np non-NULL) | YES (caller's put) | ❌ LEAK? See notes | Callee `of_mdiobus_register` may already have released the reference on error, leading to **excess put** (double‑put). |
| 1396 (success path) | err ≥ 0 → store mii_bus, fallthrough to out → L1398 put, return 0 | YES (if mdio_np non-NULL) | YES (caller's put) | ✅ (assuming callee took its own ref) | If callee takes a separate reference, caller’s put leaves ref held by bus; no leak. |

**Critical note**: The warning is a “refcount excess put” on the `mdio_np` kref at line 1398. On the error path, `of_mdiobus_register()` likely consumes (or internally puts) the reference on failure, so the caller’s subsequent `of_node_put(mdio_np)` is an extra put that drives the counter below zero.

[NEED_SOURCE] of_mdiobus_register

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`of_mdiobus_register()` error path likely releases the node reference internally; the caller’s unconditional `of_node_put(mdio_np)` at line 1398 then becomes a double‑put, causing the reported refcount excess put.
```
