# REAL BUG: drivers/gpu/drm/vkms/vkms_configfs.c:836 vkms_configfs_register()

**Confidence**: MEDIUM | **Counter**: `vkms_subsys.su_group.cg_item.ci_kref.refcount.refs.counter`

## Reasoning

| L836 | error (ret != 0) | YES (config_group_init) | NO (no put at error path) | ❌ LEAK | configfs_register_subsystem failed, but initial reference from config_group_init never released → refcount leak |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L829 | success (ret=0) | NO (before get) | N/A | ✅ | is_configfs_registered true → config_group_init skipped |
| L836 | success (ret==0) | YES (config_group_init) | NO (no immediate put; ref held for device lifetime) | ✅ | configfs_register_subsystem succeeded → ref transferred to configfs subsystem management; put occurs on unregister |
| L836 | error (ret != 0) | YES (config_group_init) | NO (no put at error path) | ❌ LEAK | configfs_register_subsystem failed, but initial reference from config_group_init never released → refcount leak |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`config_group_init` establishes an initial kref reference; when `configfs_register_subsystem` fails, the function returns without calling any matching put, leaking the reference.
```
