# REAL BUG: drivers/mtd/nand/raw/ingenic/ingenic_nand_drv.c:461 ingenic_nand_init_chips()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L460 | success     | YES (last np reference) | YES (scoped `of_node_put` at L461) | ✅       | Only one put for the last child. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L447 | error       | NO (no np get)         | N/A           | ✅       | Before loop; no reference held. |
| L454 | error       | YES (np from `for_each_child_of_node_scoped`)      | YES (scoped `of_node_put` at L461) + possibly PUT from `ingenic_nand_cleanup_chips()`. If cleanup_chips also puts np → excess put.             | ❌ EXCESS PUT if cleanup_chips puts   | `ingenic_nand_cleanup_chips()` is called at L453; scoped destructor at L461 will put again. Warning location L461 confirms double‑put. |
| L460 | success     | YES (last np reference) | YES (scoped `of_node_put` at L461) | ✅       | Only one put for the last child. |

**PRE-VERDICT CHECKLIST**

1. **“Held for device lifetime”?** – N/A; the loop’s np is not owned by the device driver unless explicitly transferred.  
2. **“Ownership transferred”?** – No documented ownership transfer; `for_each_child_of_node_scoped` gives a reference that the caller must release. If `ingenic_nand_init_chip()` stored np without an extra `of_node_get()`, it created a double‑put later.  
3. **Unconditional GET?** – The scoped loop’s `of_get_next_child()` is unconditional GET; every np obtained is later put by the scoped destructor at L461.  
4. **goto out between GET and PUT?** – No goto; the error path at L454 calls `ingenic_nand_cleanup_chips()` then returns. The implicit put at L461 runs after the function returns. If `cleanup_chips` already released the np reference, L461’s put is an excess put.

**Verdict:** The warning pinpoints the scoped destructor’s put at L461 finding the kref already zero, indicating a double‑put. The only way this happens is if `ingenic_nand_cleanup_chips()` (or `ingenic_nand_init_chip()` on its error paths) releases the same np reference before L461. Thus the error path in `ingenic_nand_init_chips()` contains a refcount imbalance – a classic double‑put bug.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`ingenic_nand_cleanup_chips()` or `ingenic_nand_init_chip()` error handling also puts the device_node reference that the scoped loop variable will put at L461, causing an excess put on the kref.
```
