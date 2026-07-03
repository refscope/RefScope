# REAL BUG: drivers/of/unittest.c:1223 of_unittest_pci_dma_ranges()

**Confidence**: HIGH | **Counter**: `np->kobj.kref.refcount.refs.counter`

## Reasoning

| L1223 (fallthrough) | normal end of function | YES | YES | ✅ | of_node_put(np) releases the reference |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1181 | early return (CONFIG_PCI disabled) | NO (before get) | N/A | ✅ | No get occurred |
| L1187 | early return (np==NULL) | NO (get returned NULL) | N/A | ✅ | of_find_node_by_path returned NULL, no reference acquired |
| L1192 | error return (parser init fails) | YES (np non‑NULL) | NO | ❌ LEAK | np holds a reference from of_find_node_by_path, but function returns without of_node_put |
| L1223 (fallthrough) | normal end of function | YES | YES | ✅ | of_node_put(np) releases the reference |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`of_find_node_by_path()` at L1183 acquires a reference on `np`. The error‑return path at L1192 (when `of_pci_dma_range_parser_init()` fails) returns without calling `of_node_put()`, leaking the reference. The warning at L1223 indicates the reference is never released on all paths.
```
