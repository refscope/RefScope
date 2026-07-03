# REAL BUG: drivers/infiniband/hw/mlx4/sysfs.c:753 register_one_pkey_tree()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L724 (return 0)      | success | YES | NO | ❌ LEAK | No put for device_parent ref acquired by `kobject_get` at L711 |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L706 (goto fail_dev) | error | NO (GET at L711 not reached) | N/A | ✅ | |
| L716 (goto err_ports) | error | YES (L711 executed) | YES (two puts at L738-L739) | ❌ LEAK + OVER‑PUT | Double put on device_parent |
| L722 (goto err_add)  | error | YES | YES (falls through to err_ports → double put) | ❌ LEAK + OVER‑PUT | Double put on device_parent |
| L724 (return 0)      | success | YES | NO | ❌ LEAK | No put for device_parent ref acquired by `kobject_get` at L711 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`kobject_get` on `dev->pkeys.device_parent[slave]` is leaked on success and double‑freed on error paths, causing severe refcount inconsistency.
```
