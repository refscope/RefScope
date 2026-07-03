# REAL BUG: drivers/clk/mediatek/clk-mt8173-infracfg.c:139 clk_mt8173_infracfg_probe()

**Confidence**: HIGH | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

| L116 | goto unregister_clk_hw (error) | YES (get succeeded) | YES (of_clk_del_provider at L119) | ✅ | |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L102 | error (ENOMEM) | NO (before get) | N/A  | ✅ | |
| L110 | error (r)     | NO (before get) | N/A  | ✅ | |
| L112 | goto unregister_gates | NO (before get) | N/A  | ✅ | |
| L114 | goto unregister_cpumuxes (error after get) | YES (unconditional) | NO  | ❌ LEAK | of_clk_del_provider / of_node_put missing |
| L116 | goto unregister_clk_hw (error) | YES (get succeeded) | YES (of_clk_del_provider at L119) | ✅ | |
| L117 | success | YES | N/A (ref held by provider, cleaned on device removal) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_clk_add_hw_provider` unconditionally increments node refcount; error path at L114 jumps to `unregister_cpumuxes` which never releases it.
```
```
