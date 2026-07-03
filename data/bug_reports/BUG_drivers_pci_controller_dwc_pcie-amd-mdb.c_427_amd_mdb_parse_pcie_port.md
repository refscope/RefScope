# REAL BUG: drivers/pci/controller/dwc/pcie-amd-mdb.c:427 amd_mdb_parse_pcie_port()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L418 | success return (0) | YES (node from loop) | NO | ❌ LEAK | early return without of_node_put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L416 | error return (IS_ERR) | YES (node from loop) | NO | ❌ LEAK | early return without of_node_put |
| L418 | success return (0) | YES (node from loop) | NO | ❌ LEAK | early return without of_node_put |
| L421 | no child (ENODEV) | NO (loop not entered) | N/A | ✅ | no ref held |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
for_each_child_of_node_with_prefix acquires a reference on pcie_port_node; both early return paths inside the loop (error and success) miss of_node_put, leaking the reference.
```
