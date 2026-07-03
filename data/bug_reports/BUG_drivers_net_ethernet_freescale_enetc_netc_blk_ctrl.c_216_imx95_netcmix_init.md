# REAL BUG: drivers/net/ethernet/freescale/enetc/netc_blk_ctrl.c:216 imx95_netcmix_init()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

[NEED_SOURCE] netc_of_pci_get_bus_devfn

## Full Response

```
## Path Table

| Line   | Return Type | GET Done? (gchild) | PUT Done? (cleanup) | Extra Put from callee? | Balanced? | Notes |
|--------|-------------|-------------------|---------------------|------------------------|-----------|-------|
| L179   | error       | YES (inner loop got gchild) | YES (scoped cleanup at function exit) | Likely YES (netc_of_pci_get_bus_devfn may put gchild) | ❌ LEAK | If callee drops ref, excess put at cleanup |
| L190   | error       | YES                | YES                  | Likely YES             | ❌ LEAK | Same |
| L202   | error       | YES                | YES                  | Likely YES             | ❌ LEAK | Same |
| L215   | success     | YES (on final loop iteration) | YES (scoped cleanup at function exit) | Likely YES             | ❌ LEAK | Same |

All early returns (L179, L190, L202) and the final return (L215) pass through a path where `netc_of_pci_get_bus_devfn(gchild)` is called, and the scoped cleanup later calls `of_node_put(gchild)`. If the callee also releases the reference on `gchild` (which smatch’s counter analysis suggests), the reference count becomes negative at the cleanup point (line 216), causing an “excess put.”

Note: The exact implementation of `netc_of_pci_get_bus_devfn` is not provided. I need to investigate whether it indeed calls `of_node_put` on the passed node.

[NEED_SOURCE] netc_of_pci_get_bus_devfn

## VERDICT: REAL_BUG

## CONFIDENCE: MEDIUM

The scoped cleanup at line 216 triggers an excess kobject_put on the device_node's kref, as tracked by smatch. The most likely cause is that `netc_of_pci_get_bus_devfn(gchild)` internally drops the node's reference, so the subsequent automatic put from the loop macro causes a double‐put on all return paths that followed that function call. Without the callee’s source this cannot be fully confirmed, but the refcount tracking strongly indicates it. The fix would be to ensure `netc_of_pci_get_bus_devfn` does not release the reference, or to adjust the caller to account for that release (e.g., by not relying on macro cleanup).
```
