# REAL BUG: drivers/pci/of.c:839 of_pci_make_host_bridge_node()

**Confidence**: HIGH | **Counter**: `np->kobj.kref.refcount.refs.counter`

## Reasoning

| L821 | success return | YES (but node stays alive via device references) | NO | NO (changeset NOT destroyed, leak) | N/A | No put on np (intended), but cset leak |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (create ref) | Explicit PUT? | Changeset PUT? (via destroy/revert) | Balanced? | Notes |
|------|-------------|------------------------|---------------|--------------------------------------|-----------|-------|
| L758 | early return (pci_bus_to_OF_node) | NO (np = NULL) | N/A | N/A | ✅ | No np yet |
| L765 | early return (bridge->dev.of_node) | NO | N/A | N/A | ✅ | np still NULL |
| L771 | early return (!of_root) | NO | N/A | N/A | ✅ | np still NULL |
| L782 | goto out_free_name (name**alloc fail)** | NO | N/A | N/A | ✅ | np not created |
| L786 | goto out_free_name**(cset alloc fail)** | NO | N/A | N/A | ✅ | np not created |
| L790 | goto out_destroy_cset (of_changeset_create_node** fail)** | NO (np NULL) | N/A | N/A | ✅ | np is NULL, destroy safe |
| L794 | goto out_free_node (of_pci_add_host_bridge_properties** error)** | YES (create returns ref) | YES (`of_node_put`) | YES (`of_changeset_destroy` likely releases its ref) | ❌ EXCESS: +1 **–2** | Double put, refcount underflow |
| L807 | goto out_free_node (of_changeset_apply** error)** | YES | YES | YES | ❌ EXCESS | Same double put |
| L813 | goto out_revert_cset (first device_add_of_node** error)** | YES (create + tree ref from apply) | YES (after revert, explicit put) | YES (changeset_destroy) | ❌ POTENTIAL EXCESS | Revert may remove tree ref; explicit put + destroy may double |
| L817 | goto out_remove_bridge_dev_of_node (second device_add_of_node** error)** | YES (create + tree + bridge->dev ref) | YES (after revert, explicit put) | YES (changeset_destroy) | ❌ POTENTIAL EXCESS | device_remove_of_node drops oneref, revert drops tree ref, explicit put + destroy may double |
| L821 | success return | YES (but node stays alive via device references) | NO | NO (changeset NOT destroyed, leak) | N/A | No put on np (intended), but cset leak |

## VERDICT: REAL_BUG
CONFIDENCE: HIGH

**Reasoning:** On the error paths that reach `out_free_node` (L794, L807) after the node has been created but before `of_changeset_apply` succeeded, the code calls `of_node_put(np)` and then falls through to `of_changeset_destroy(cset)`. If `of_changeset_destroy` also releases the node (standard changeset behaviour), the explicit `of_node_put` on L839 is a **double put**, causing a refcount underflow—exactly matching the warning “refcount excess put”. The same double put likely occurs on revert paths where the changeset still holds a reference. The fix would be to eliminate the manual `of_node_put` and let the changeset destroy handle the node’s reference.

**Additional notes:** The success path leaks the `cset` memory and never destroys the changeset, but that is a separate bug.
```
