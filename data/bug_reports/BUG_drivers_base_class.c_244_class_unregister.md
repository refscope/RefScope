# REAL BUG: drivers/base/class.c:244 class_unregister()

**Confidence**: HIGH | **Counter**: `sp->subsys.kobj.kref.refcount.refs.counter`

## Reasoning

| 244  | `return` (sp non-NULL) | YES (class_to_subsys succeeded) | YES (via kset_unregister AND subsys_put) | ❌ EXCESS PUT | kset_unregister already does a put (contract says →kobject_put), then subsys_put does a second put on same kobj counter |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 238  | `return` (sp NULL) | NO (get failed) | N/A | ✅ | early return before any get |
| 244  | `return` (sp non-NULL) | YES (class_to_subsys succeeded) | YES (via kset_unregister AND subsys_put) | ❌ EXCESS PUT | kset_unregister already does a put (contract says →kobject_put), then subsys_put does a second put on same kobj counter |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
subsys_put(sp) on line 244 is an extra put after kset_unregister(&sp->subsys) already released the reference, causing a double-put on sp->subsys.kobj.kref.
```
