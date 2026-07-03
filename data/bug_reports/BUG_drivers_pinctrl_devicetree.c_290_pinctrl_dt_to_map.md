# REAL BUG: drivers/pinctrl/devicetree.c:290 pinctrl_dt_to_map()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L286 | return 0 (success) | YES | NO | ❌ LEAK | successful completion still leaks the np reference |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L217 | return 0 (no DT) | NO (before get) | N/A | ✅ | of_node_get not called if np == NULL |
| L229 | goto err (ENOMEM) | YES | NO | ❌ LEAK | err label only calls pinctrl_dt_free_maps(), no of_node_put(np) |
| L236 | goto err (ENODEV) | YES | NO | ❌ LEAK | same err label |
| L238 | break → L286 return 0 | YES | NO | ❌ LEAK | normal exit after loop, no put |
| L265 | goto err (invalid phandle) | YES | NO | ❌ LEAK | of_node_put(np_config) is for different node, not np |
| L275 | goto err (dt_to_map_one_config fail) | YES | NO | ❌ LEAK | same err label, np_config already put but np not |
| L282 | goto err (dummy state fail) | YES | NO | ❌ LEAK | same err label |
| L286 | return 0 (success) | YES | NO | ❌ LEAK | successful completion still leaks the np reference |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get(np)` at L221 unconditionally acquires a reference that is never released by any exit path; every return after L221 leaks the kref.
```
