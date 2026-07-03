# REAL BUG: drivers/of/unittest.c:1261 of_unittest_pci_empty_dma_ranges()

**Confidence**: HIGH | **Counter**: `np->kobj.kref.refcount.refs.counter`

## Reasoning

| L1261 | success path (end of function) | YES | YES | ✅ | of_node_put(np) properly released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1230 | early return (CONFIG_PCI disabled) | NO (before get) | N/A | ✅ | No get executed |
| L1235 | early return (np == NULL) | NO (get failed) | N/A | ✅ | Conditional get; no ref held because np is NULL |
| L1240 | error return (parser_init fails) | YES (np non‑NULL, get succeeded) | NO | ❌ LEAK | Ref acquired at L1233 is never released on this path |
| L1261 | success path (end of function) | YES | YES | ✅ | of_node_put(np) properly released |

**PRE‑VERDICT CHECKLIST**
1. **"Held for device lifetime"?** Not applicable; this is a test function, not a probe.
2. **"Ownership transferred"?** No evidence; np is never stored in any long‑lived structure with documented cleanup.
3. **Unconditional GET?** No – `of_find_node_by_path` is conditional (returns NULL on failure), but on the error path after parser_init, `np` is known non‑NULL, so GET is active.
4. **goto out between GET and PUT?** Not exactly a `goto`, but the `return` inside the `if (of_pci_dma_range_parser_init(...))` block acts identically: it exits without calling `of_node_put`.

The path table shows a clear refcount imbalance: the error path at L1240 obtains a reference (`np != NULL`) but does not release it, while the main success path correctly puts. This is a genuine refcount leak, even though the warning’s label “excess put” primarily points to L1261. The underlying bug is the missing put on the parser‑init failure path.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
of_pci_dma_range_parser_init failure path (L1240) returns without of_node_put, leaking the reference acquired at L1233.
```
