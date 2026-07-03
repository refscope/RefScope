# REAL BUG: drivers/net/wireless/ath/ath11k/ahb.c:1069 ath11k_ahb_fw_resources_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1064 | error (ret) via `err_unregister` | YES | YES | ✅ | `err_unregister` label calls `platform_device_unregister(pdev)` then `of_node_put(node)`; reachable from all goto error paths after platform device registration |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L981 | success (0) | NO (before get) | N/A | ✅ | `fixed_fw_mem` false, early return before `of_get_child_by_name` |
| L990 | success (0) | NO (get returned NULL) | N/A | ✅ | node is NULL, no reference taken |
| L1004 | error (ret) | YES | NO | ❌ LEAK | `ath11k_ahb_setup_msa_resources` failed, return without `of_node_put(node)` |
| L1013 | error (PTR_ERR) | YES | YES | ✅ | `IS_ERR(pdev)` branch explicitly calls `of_node_put(node)` before return |
| L1052 | success (0) | YES | YES | ✅ | normal path: `of_node_put(node)` before `return 0` |
| L1064 | error (ret) via `err_unregister` | YES | YES | ✅ | `err_unregister` label calls `platform_device_unregister(pdev)` then `of_node_put(node)`; reachable from all goto error paths after platform device registration |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_get_child_by_name()` acquires a refcount at L984. The error path `ath11k_ahb_setup_msa_resources()` failure at L1000-1004 returns immediately without releasing the node, leaking the reference. All other paths correctly call `of_node_put()`.
```
