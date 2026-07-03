# REAL BUG: drivers/pmdomain/core.c:2742 of_genpd_add_provider_simple()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2731 (return 0) | success | YES (of_node_get) | Ownership transferred, released on provider removal | ✅ | Balanced via future of_genpd_del_provider |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2681 | error (-EINVAL) | NO | N/A | ✅ | before any get |
| L2684 | error (-ENODEV) | NO | N/A | ✅ | before any get |
| L2687 | error (-EINVAL) | NO | N/A | ✅ | before any get |
| L2707 | error (device_add) | YES (get_dev_from_fwnode) | YES (put_device at L2703) | ✅ | fwnode dev get/put balanced, no other get |
| L2714 (goto err_del) | error (OPP table) | YES (get_dev_from_fwnode) | YES (put_device at L2703) | ✅ | genpd_add_provider not yet called |
| L2727 (goto err_opp) | error (genpd_add_provider) | YES (of_node_get via genpd_add_provider) | NO (no of_node_put in error path) | ❌ LEAK | **LEAK** – np reference not released |
| L2731 (return 0) | success | YES (of_node_get) | Ownership transferred, released on provider removal | ✅ | Balanced via future of_genpd_del_provider |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`genpd_add_provider()` performs unconditional `of_node_get(np)`. On failure at line 2727 the error path (`err_opp` → `err_del`) lacks `of_node_put`, leaking the device_node reference.
```
