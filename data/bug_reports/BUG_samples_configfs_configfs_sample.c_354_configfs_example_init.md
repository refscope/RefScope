# REAL BUG: samples/configfs/configfs_sample.c:354 configfs_example_init()

**Confidence**: HIGH | **Counter**: `subsys->su_group.cg_item.ci_kref.refcount.refs.counter`

## Reasoning

| L343 → L352 (via goto out_unregister) | error       | YES (for current subsys) | NO (no release of current subsys) | ❌ LEAK | config_group_init increments refcount, no corresponding put on error |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L346 | success     | YES (all subsys inited) | YES (all registered, will be unregistered in module exit) | ✅ | Module holds until exit |
| L343 → L352 (via goto out_unregister) | error       | YES (for current subsys) | NO (no release of current subsys) | ❌ LEAK | config_group_init increments refcount, no corresponding put on error |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
config_group_init() unconditionally increments the reference count on subsys->su_group, but the error path at L343 → L352 does not release that reference, causing a leak.
```
