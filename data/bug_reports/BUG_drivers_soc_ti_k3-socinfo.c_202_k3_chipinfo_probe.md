# REAL BUG: drivers/soc/ti/k3-socinfo.c:202 k3_chipinfo_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| soc_device_register fail | goto err_free_rev → kfree(revision) → err → kfree(soc_dev_attr) → return ret | YES | NO | ❌ LEAK | of_node_put never called; ref held from L202 |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| base IS_ERR | error (return PTR_ERR) | NO | N/A | ✅ | Before of_find_node_by_path |
| regmap IS_ERR | error (return PTR_ERR) | NO | N/A | ✅ | |
| regmap_read fail | error (return ret) | NO | N/A | ✅ | |
| mfg != TI | error (return -ENODEV) | NO | N/A | ✅ | |
| kzalloc fail | error (return -ENOMEM) | NO | N/A | ✅ | |
| partno_to_names fail | goto err → kfree → return ret | NO | N/A | ✅ | err has only kfree(soc_dev_attr), no put |
| variant_to_sr fail | goto err → kfree → return ret | NO | N/A | ✅ | |
| soc_device_register success | return 0 | YES | YES | ✅ | of_node_put(node) called at L204 |
| soc_device_register fail | goto err_free_rev → kfree(revision) → err → kfree(soc_dev_attr) → return ret | YES | NO | ❌ LEAK | of_node_put never called; ref held from L202 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_find_node_by_path("/")` at L202 acquires a reference, but the `soc_device_register` error path `goto err_free_rev` L208-L216 omits `of_node_put`, leaking the root device_node reference.
```
