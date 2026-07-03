# REAL BUG: drivers/of/resolver.c:126 update_usages_of_a_phandle_reference()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L125 | success     | YES (accumulated)  | NO                  | ❌ LEAK    | all overlay gets from loop never released |

## Full Response

```
| Line | Return Type | GET Done? (overlay) | PUT Done? (overlay) | Balanced? | Notes |
|------|-------------|---------------------|---------------------|-----------|-------|
| L83  | error       | NO (before get)    | N/A                 | ✅         |       |
| L93  | error       | NO (before get)    | N/A                 | ✅         |       |
| L99  | error       | NO (before get)    | N/A                 | ✅         |       |
| L104 | error       | NO (before get)    | N/A                 | ✅         |       |
| L108 | continue    | YES (L106 get)     | NO                  | ❌ LEAK    | overlay ref leaked on NULL refnode |
| L117 | error       | YES (L106 get)     | NO                  | ❌ LEAK    | refnode put, overlay never put |
| L120 | error       | YES (L106 get)     | NO                  | ❌ LEAK    | refnode put, overlay never put |
| L125 | success     | YES (accumulated)  | NO                  | ❌ LEAK    | all overlay gets from loop never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get(overlay)` is called each loop iteration, but `of_node_put(overlay)` is never called; every path after L106 leaks the overlay reference.
```
