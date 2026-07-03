# REAL BUG: drivers/pci/controller/dwc/pcie-eswin.c:178 eswin_pcie_parse_ports()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

node’s kref, reported at line 178—the call to `eswin_pcie_parse_port()`. This indicates that `eswin_pcie_parse_port()` performs an extra `of_node_put` on the `of_port` node after the macro has already obtained and will later release the reference, leading to a double‑put and refcount underflow.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (of_node) | PUT Done? (of_node) | Balanced? | Notes |
|------|-------------|---------------------|---------------------|-----------|-------|
| L165 | success (return 0) | YES – `for_each_available_child_of_node_scoped` takes a reference on the child at every iteration | YES – the scoped macro automatically puts the child at the end of each iteration and when going out of scope | ✅ | Normal loop exit; all children correctly ref‑counted |
| L167 | error (goto err_port) | YES – the current child was obtained with a reference | YES – the scoped cleanup runs on `goto` because the variable leaves scope | ✅ | Macro’s `__cleanup__` releases the current child; no leak |
| L171 | error (return ret after list cleanup) | YES (same as above) | YES (same as above) | ✅ | The child node is put before the error return; the list cleanup does not touch device nodes |

The main function itself has no missing `put` or `get` issues. The warning is an **excess put** on the device node’s kref, reported at line 178—the call to `eswin_pcie_parse_port()`. This indicates that `eswin_pcie_parse_port()` performs an extra `of_node_put` on the `of_port` node after the macro has already obtained and will later release the reference, leading to a double‑put and refcount underflow.

## VERDICT: REAL_BUG
CONFIDENCE: MEDIUM  
`eswin_pcie_parse_port()` likely calls `of_node_put()` without a matching `of_node_get()`, clashing with the automatic put from `for_each_available_child_of_node_scoped`. The main function’s refcounting is correct; the bug is in the callee’s interaction with the node reference.
```
