# REAL BUG: drivers/gpu/drm/xe/xe_hw_engine_class_sysfs.c:680 xe_hw_engine_class_sysfs_init()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L680 | success / devm error | YES (init + all child refs) | YES (devm action cleans up children and puts) | ✅ | devm_add_action_or_reset either registers cleanup (success) or runs it on failure |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L635 | error (early return) | NO | N/A | ✅ | before kobject_init |
| L640 | goto err_object | YES (init) | YES (via err_object) | ✅ | kobject_add failure; init ref put |
| L655 | goto err_object | YES (init) | YES (via err_object) | ✅ | no child created yet |
| L658 | goto err_object | YES (init) | YES (via err_object) | ✅ | child creation failed, no extra ref on kobj |
| L663 | goto err_object | YES (init + child’s parent ref) | NO (only init put; child still holds ref on kobj) | ❌ LEAK | child created by kobj_xe_hw_engine_class; error path does not remove child |
| L665 | goto err_object | YES (as above) | NO | ❌ LEAK | same as L663 |
| L680 | success / devm error | YES (init + all child refs) | YES (devm action cleans up children and puts) | ✅ | devm_add_action_or_reset either registers cleanup (success) or runs it on failure |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error paths after creating child kobjects (L663, L665) only call kobject_put(kobj) without removing the child, leaving the parent’s refcount permanently elevated and leaking the reference held by the child.
```
