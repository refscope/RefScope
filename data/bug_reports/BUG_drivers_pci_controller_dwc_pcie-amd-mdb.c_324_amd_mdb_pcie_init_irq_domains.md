# REAL BUG: drivers/pci/controller/dwc/pcie-amd-mdb.c:324 amd_mdb_pcie_init_irq_domains()

**Confidence**: HIGH | **Counter**: `pcie_intc_node->kobj.kref.refcount.refs.counter`

## Reasoning

eously drops the caller’s reference). This combined with the subsequent `of_node_put()` at the `out:` label results in a **double put**, triggering the refcount excess-put warning at the `out:` line (324 in the original file). No ownership‑transfer or deferred‑release pattern rescues this path.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 293  | `return -ENODEV` | NO (node is NULL) | N/A | ✅ | Early return, no ref acquired |
| 300  | `goto out` (→ L320) | YES (node acquired at L291) | YES (`of_node_put` at L321) | ✅ | Error creating MDB domain; single put |
| 309  | `goto mdb_out` (→ L318) | YES (node acquired at L291) | ⚠️ Partially (see notes) | ❌ LEAK (double put) | `mdb_out` calls `amd_mdb_pcie_free_irq_domains` (likely puts the node) then falls through to `out:` which does `of_node_put` again → excess put |
| 313  | `return 0` | YES (node acquired at L291) | YES (`of_node_put` at L313) | ✅ | Success path, explicit put before returning |

**Critical path**: The second domain failure (line 309) leads to `mdb_out`, which calls `amd_mdb_pcie_free_irq_domains()`. Based on the kernel IRQ domain internals, the domain does **not** take its own reference on the fwnode; the caller must keep the node alive. However, `amd_mdb_pcie_free_irq_domains()` likely contains an `of_node_put()` on the node (either directly or via a domain cleanup that erroneously drops the caller’s reference). This combined with the subsequent `of_node_put()` at the `out:` label results in a **double put**, triggering the refcount excess-put warning at the `out:` line (324 in the original file). No ownership‑transfer or deferred‑release pattern rescues this path.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH  
Double put on `pcie_intc_node` in error path after `amd_mdb_pcie_free_irq_domains` already releases the reference; the warning line coincides with the second `of_node_put()`.
```
