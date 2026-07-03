# REAL BUG: lib/kobject.c:257 kobject_add_internal()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L257 (return 0) | success (create_dir ok) | YES (parent get succeeded) | NO | ❌ LEAK | No kobject_put(parent) on success |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L215 (return -ENOENT) | error | NO (before get) | N/A | ✅ | kobj NULL check before any get |
| L221 (return -EINVAL) | error | NO (before get) | N/A | ✅ | empty name check before any get |
| L249 (goto error) | error (create_dir fails) | YES (parent get succeeded, or additional kset get) | YES (kobject_put(parent)) | ✅ | explicit put on error path |
| L257 (return 0) | success (create_dir ok) | YES (parent get succeeded) | NO | ❌ LEAK | No kobject_put(parent) on success |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On success path after create_dir, kobject_add_internal() returns without releasing the reference obtained via kobject_get(parent), causing a permanent refcount leak on the parent kobject.
```
