# REAL BUG: drivers/edac/edac_device_sysfs.c:556 edac_device_create_block()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L536 (return 0) | success | YES | NO | ❌ LEAK | No `kobject_put(main_kobj)` on the success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L504 (goto err_out) | error, -ENODEV | NO (main_kobj NULL) | N/A | ✅ | `kobject_get` returned NULL, no ref held |
| L516 (goto err_out) | error, -ENODEV | YES (successful get) | YES (kobject_put(main_kobj) at L515) | ✅ | Explicit put before goto |
| L531 (goto err_on_attrib) | error after sysfs failure | YES | NO | ❌ LEAK | `err_on_attrib` only puts `block->kobj`; missing `kobject_put(main_kobj)` |
| L536 (return 0) | success | YES | NO | ❌ LEAK | No `kobject_put(main_kobj)` on the success path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`kobject_get` at L500 acquires a reference on `edac_dev->kobj`. The success path (L536) and the `err_on_attrib` error path (L531) both fail to release it with `kobject_put(main_kobj)`.
```
