# REAL BUG: drivers/pci/of.c:735 of_pci_make_dev_node()

**Confidence**: HIGH | **Counter**: `np->kobj.kref.refcount.refs.counter`

## Reasoning

tern. The revert already released the caller’s reference, making the subsequent `of_node_put` incorrect. The fix is to either set `np = NULL` after `of_changeset_revert` (so the later `of_node_put` becomes a no-op) or restructure the error handling so that `of_node_put` is not called on this path.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L674 (early check) | return (void) | N/A (np not allocated) | N/A | ✅ | |
| L679 (ppnode NULL) | return | N/A | N/A | ✅ | |
| L688 (name NULL) | return | N/A | N/A | ✅ | |
| L691 (cset NULL) | goto out_free_name → return | N/A | N/A | ✅ | np not created |
| L695 (np creation fails) | goto out_destroy_cset → return | N/A (np=NULL) | N/A | ✅ | no put needed |
| L698 (of_pci_add_properties fails) | goto out_free_node | YES (create ref) | YES (of_node_put) | ✅ | |
| L701 (of_changeset_apply fails) | goto out_free_node | YES (create ref) | YES (of_node_put) | ✅ | single put, no underflow |
| **L706 (device_add_of_node fails)** | **goto out_revert_cset → fall through to out_free_node** | **YES (create ref)** | **YES (of_node_put)** BUT `of_changeset_revert` already dropped ref to 0 → **EXCESS PUT** | ❌ | **underflow: of_node_put after revert tries to release an already freed node** |
| L709–711 (success) | return | YES (create + of_node_get via device_add_of_node) | NO (deferred to device removal) | ✅ (deferred) | |

**Reasoning:**  
- On the path where `device_add_of_node` fails (≈L706), the code jumps to `out_revert_cset`, calls `of_changeset_revert(cset)`.  
- `of_changeset_revert` iterates over the changeset entries; for the ADD_NODE entry created by `of_changeset_create_node`, it detaches the node and calls `of_node_put(ce->np)`, which decrements the node’s reference to **0** and frees it.  
- After the revert, execution falls through to `out_free_node` and calls `of_node_put(np)`. At this point the node is already freed and its refcount is 0 → the extra `kobject_put` triggers a **refcount underflow**, exactly the “refcount excess put” warning.  

This is a classic ownership-double-free pattern. The revert already released the caller’s reference, making the subsequent `of_node_put` incorrect. The fix is to either set `np = NULL` after `of_changeset_revert` (so the later `of_node_put` becomes a no-op) or restructure the error handling so that `of_node_put` is not called on this path.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_changeset_revert` already drops the node’s refcount to zero; the fallthrough to `of_node_put(np)` causes a refcount underflow.
```
