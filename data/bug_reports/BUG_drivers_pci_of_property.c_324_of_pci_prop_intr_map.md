# REAL BUG: drivers/pci/of_property.c:324 of_pci_prop_intr_map()

**Confidence**: HIGH | **Counter**: `$->np->kobj.kref.refcount.refs.counter`

## Reasoning

| L312 (success)      | return 0     | YES                     | NO        | ❌ LEAK | success path still leaks all gathered np references |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L228 | error       | NO (before any parse) | N/A        | ✅ | No parses executed |
| L272 | early return| NO (map_sz=0 means all parses failed) | N/A | ✅ | out_irq[].np set NULL on all failures |
| L276 | error (-ENOMEM) | YES (successful parses held references in out_irq[].np) | NO        | ❌ LEAK | map_sz>0 → at least one parse succeeded, but no of_node_put for np |
| L300 (goto failed) | error        | YES (references held)   | NO        | ❌ LEAK | failed label only kfree(int_map), missing of_node_put |
| L301 (goto failed) | error        | YES                     | NO        | ❌ LEAK | same as above |
| L302 (goto failed) | error        | YES                     | NO        | ❌ LEAK | same as above |
| L312 (success)      | return 0     | YES                     | NO        | ❌ LEAK | success path still leaks all gathered np references |
```

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_irq_parse_raw()` increments the refcount on the interrupt-parent node and stores it in `out_irq[].np`; the function never calls `of_node_put()` on those nodes before returning, leaking every such reference on all paths after a successful parse.
```
