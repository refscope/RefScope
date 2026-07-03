# REAL BUG: drivers/pci/controller/plda/pcie-plda-host.c:419 plda_pcie_init_irq_domains()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

in_add` takes a fwnode reference (`fwnode_handle_get`) and, if a subsequent allocation fails, calls `fwnode_handle_put` (→ `of_node_put`) before returning NULL. The caller's explicit `of_node_put` in error paths then causes an excess put on the device node, matching the refcount underflow warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L392 | early error (`pcie_intc_node` NULL) | NO (of_get_next_child returned NULL) | NO | ✅ | no ref held |
| L401 | error (event_domain allocation fails) | YES (L389) | YES (L400) + **implicit put** by `irq_domain_create_linear` on failure | ❌ **EXCESS PUT** | double put: caller's `of_node_put` + domain's own put on error |
| L411 | error (intx_domain allocation fails) | YES (L389) | YES (L410) + **implicit put** by `irq_domain_create_linear` on failure | ❌ **EXCESS PUT** | double put |
| L419 | success (return) | YES (L389) | YES (L416) | ✅ | domain holds its own ref; caller drops original. Balanced. |

**Why implicit put?** `irq_domain_create_linear` → `__irq_domain_add` takes a fwnode reference (`fwnode_handle_get`) and, if a subsequent allocation fails, calls `fwnode_handle_put` (→ `of_node_put`) before returning NULL. The caller's explicit `of_node_put` in error paths then causes an excess put on the device node, matching the refcount underflow warning.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`irq_domain_create_linear` already puts the of_node on failure; error paths at L401/L411 double-put with additional `of_node_put`, causing refcount underflow.
```
