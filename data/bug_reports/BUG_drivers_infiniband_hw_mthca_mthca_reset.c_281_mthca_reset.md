# REAL BUG: drivers/infiniband/hw/mthca/mthca_reset.c:281 mthca_reset()

**Confidence**: HIGH | **Counter**: `$->dev.kobj.kref.refcount.refs.counter`

## Reasoning

aller must call `pci_dev_put()` on the `from` device before the next call. Since the old `bridge` pointer is overwritten, its reference is lost, causing a refcount leak for every device that is not the desired bridge. This persistent mismatch between get and put makes the refcounting inconsistent.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| while loop (iterates after non-match) | (overwrites bridge) | YES (each pci_get_device returns new ref) | NO (previous bridge ref not released) | ❌ LEAK | Overwrites 'bridge' without pci_dev_put on previous device. Each non-matching device leaks a reference. |
| Error paths via `goto put_dev`, `goto free_hca`, `goto free_bh` → final `return err` | error return | Final bridge ref held (if non-NULL) | YES (via `pci_dev_put(bridge)` at `put_dev`) | ✅ | All error exits eventually call `put_dev`. |
| Success path (falls through `put_dev`) | success return | Final bridge ref held (if non-NULL) | YES (via `pci_dev_put(bridge)`) | ✅ | |

**Key Issue**: The `while` loop uses `bridge = pci_get_device(..., bridge)` without releasing the previous `from` device. According to the contract, the caller must call `pci_dev_put()` on the `from` device before the next call. Since the old `bridge` pointer is overwritten, its reference is lost, causing a refcount leak for every device that is not the desired bridge. This persistent mismatch between get and put makes the refcounting inconsistent.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `while`-loop iteration in `mthca_reset()` leaks PCI device references because `pci_get_device()` returns a new reference each time and the code overwrites `bridge` without calling `pci_dev_put()` on the previous one, violating the iterative traversal contract.
```
