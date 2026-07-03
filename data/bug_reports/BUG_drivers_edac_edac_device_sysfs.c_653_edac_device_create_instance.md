# REAL BUG: drivers/edac/edac_device_sysfs.c:653 edac_device_create_instance()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L646 (return 0)       | success                        | YES (L610)   | **NO** | ❌ LEAK | `main_kobj` never put; reference leaked |

## Full Response

```
| Line | Return Type | GET Done? (main_kobj) | PUT Done? (main_kobj) | Balanced? | Notes |
|------|-------------|----------------------|----------------------|-----------|-------|
| L613 (goto err_out)   | error (NULL main_kobj)        | NO (get failed) | N/A   | ✅ | `kobject_get` returned NULL, no ref held |
| L623 (goto err_out)   | error (kobject_init_and_add fail) | YES (L610)   | YES (L622) | ✅ | explicit `kobject_put(main_kobj)` before goto |
| L638 (goto err_release_instance_kobj → L649-650, L653) | error (block creation fail) | YES (L610)   | **NO** | ❌ LEAK | `main_kobj` never put; only `instance->kobj` is put |
| L646 (return 0)       | success                        | YES (L610)   | **NO** | ❌ LEAK | `main_kobj` never put; reference leaked |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`kobject_get(&edac_dev->kobj)` at L610 is never released on the success path (L646) or on the block-creation error path (L638); the comment suggests the reference is needed for the instance’s lifetime but the pointer is not stored anywhere to be put later.
```
