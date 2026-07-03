# REAL BUG: drivers/pmdomain/mediatek/mtk-pm-domains.c:1287 scpsys_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1276 | return 0                  | YES for each added domain | NO (handled by driver remove) | ✅ | Provider registered, refs held by PM core; cleanup deferred to `scpsys_remove()` |

## Full Response

```
| Line | Return Type | GET Done? (domain kref) | PUT Done? (domain kref) | Balanced? | Notes |
|------|-------------|--------------------------|---------------------------|-----------|-------|
| L1218 | error       | NO (before any domain add) | N/A                      | ✅ | return -EINVAL; |
| L1224 | error       | NO                          | N/A                      | ✅ | return -ENOMEM; |
| L1234 | error       | NO                          | N/A                      | ✅ | return -ENODEV; |
| L1239 | error       | NO                          | N/A                      | ✅ | return PTR_ERR(scpsys->base); |
| L1245 | error       | NO                          | N/A                      | ✅ | scpsys_get_bus_protection failed, return ret; |
| L1266 | return early| N/A (no domains added)      | N/A                      | ✅ | ret==-ENODEV, no child nodes, no cleanup |
| L1256 | goto err_cleanup_domains | YES for domains added up to failure (≤ N added) | YES for ALL `num_domains` (capacity) | ❌ EXCESS PUT | `scpsys_domain_cleanup` iterates over full `num_domains`, PUT on uninitialized domains |
| L1261 | goto err_cleanup_domains | YES for domains added up to this point | YES for ALL `num_domains` | ❌ EXCESS PUT | same as above |
| L1272 | goto err_cleanup_domains | YES for all domains added in loop | YES for ALL `num_domains` | ❌ EXCESS PUT | `of_genpd_add_provider_onecell` failed, cleanup over‑puts uninitialized entries |
| L1276 | return 0                  | YES for each added domain | NO (handled by driver remove) | ✅ | Provider registered, refs held by PM core; cleanup deferred to `scpsys_remove()` |

---

```
VERDICT: REAL_BUG
CONFIDENCE: HIGH
```

`scpsys_probe` sets `pd_data.num_domains = num_domains` (total capacity) but only initialises a domain for each available child node. `scpsys_domain_cleanup` likely calls `pm_genpd_remove()` for every index up to `num_domains`, causing a `kref_put` on uninitialised generic_pm_domain structs whose `kref` is zero — the classic excess‑put underflow.  
**[NEED_SOURCE] scpsys_add_one_domain**  
**[NEED_SOURCE] scpsys_domain_cleanup**
```
