# REAL BUG: drivers/pci/controller/pcie-mt7621.c:282 mt7621_pcie_parse_dt()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

ce (e.g., by calling `of_node_put(child)`), leading to an extra put when the scoped cleanup fires. Therefore a double-put (excess put) bug exists inside the called function `mt7621_pcie_parse_port`. The calling function’s own paths are balanced, but the bug in the callee causes the reported issue.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L266 | error (IS_ERR) | NO (before child node loop) | N/A | ✅ | No child node acquired. |
| L273 | error (of_pci_get_devfn fail) | YES (child ref acquired by `for_each_available_child_of_node_scoped`) | YES (via `__cleanup(of_node_put)` on `child` variable) | ✅ | Scoped cleanup handles the put automatically. |
| L279 | error (mt7621_pcie_parse_port fail) | YES | YES (via `__cleanup(of_node_put)`) | ✅ | Same scoped cleanup, balanced. |
| L282 | success (return 0) | YES | YES (via `__cleanup(of_node_put)`) | ❌ EXCESS PUT | The scoped cleanup calls `of_node_put(child)`. The warning on this line indicates the refcount was already zero before this put, i.e., `mt7621_pcie_parse_port()` already decremented it (likely via `of_node_put(child)`), causing a double-put. This is a real bug in the callee, but the excess manifests at this return point. |

**Reasoning**:  
The main function `mt7621_pcie_parse_dt()` itself uses correct balanced refcounting via the scoped `for_each_available_child_of_node_scoped` – every child acquire is matched by an automatic put. The warning `refcount excess put` at line 282 (the `return 0;` of this function) means the final `of_node_put(child)` from the scoped cleanup drops the refcount below zero. The only explanation is that `mt7621_pcie_parse_port()` already released the `child` node’s reference (e.g., by calling `of_node_put(child)`), leading to an extra put when the scoped cleanup fires. Therefore a double-put (excess put) bug exists inside the called function `mt7621_pcie_parse_port`. The calling function’s own paths are balanced, but the bug in the callee causes the reported issue.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
