# REAL BUG: drivers/pmdomain/mediatek/mtk-pm-domains.c:1099 scpsys_get_bus_protection_legacy()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| 1098 | success     | YES (3 gets) | NO        | ❌ LEAK   | three of_node_get(np) not released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 1037 | error       | YES (1 get)  | NO        | ❌ LEAK   | of_node_get(np) at L1030 not released |
| 1050 | error       | YES (2 gets) | NO        | ❌ LEAK   | two of_node_get(np) at L1030, L1044 not released |
| 1056 | error       | YES (2 gets) | NO        | ❌ LEAK   | two of_node_get(np) not released |
| 1073 | error       | YES (3 gets) | NO        | ❌ LEAK   | three of_node_get(np) not released |
| 1083 | error       | YES (3 gets) | NO        | ❌ LEAK   | three of_node_get(np) not released |
| 1098 | success     | YES (3 gets) | NO        | ❌ LEAK   | three of_node_get(np) not released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get(np)` is called three times without any corresponding `of_node_put(np)` on any return path, leaking device-node references.
```
