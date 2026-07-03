# REAL BUG: drivers/misc/fastrpc.c:2458 fastrpc_rpmsg_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2452 | success return | YES | YES (devices kept alive, cleaned up on remove) | ✅ | normal success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2362 | error return | NO (before any GET) | N/A | ✅ | property read failure returns early |
| L2367 | error return | NO | N/A | ✅ | domain_id < 0, no GET |
| L2380 | error return (-EPROBE_DEFER) | NO | N/A | ✅ | qcom_scm not available, no GET |
| L2392 | goto err_free_data | NO (GET not yet) | N/A | ✅ | assign_mem error before platform populate |
| L2406 | goto err_free_data | NO | N/A | ✅ | fastrpc_device_register failure before platform populate |
| L2413 | goto err_free_data | NO | N/A | ✅ | similar, before platform populate |
| L2417 | goto err_deregister_fdev | NO (no platform create yet) | N/A | ✅ | second fastrpc_device_register failure, before platform populate |
| L2422 | goto err_free_data | NO | N/A | ✅ | default domain error |
| **L2450** | **goto err_deregister_fdev** | **YES** (of_platform_populate called, partial devices created) | **NO** (missing of_platform_depopulate) | ❌ LEAK | **core bug** |
| L2452 | success return | YES | YES (devices kept alive, cleaned up on remove) | ✅ | normal success path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_platform_populate` at L2450 may create child platform devices; on error the code jumps to `err_deregister_fdev` which lacks `of_platform_depopulate`, leaving dangling krefs on the partially created devices.
```
