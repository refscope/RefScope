# REAL BUG: fs/sysfs/group.c:199 internal_create_group()

**Confidence**: HIGH | **Counter**: `$->count.counter`

## Reasoning

| L199 (grp->name NULL) | error/success | YES (L188) | NONE | 1 | 1 (L194) | ✅ | kn = kobj->sd, no creation ref |

## Full Response

```
| Line | Return Type | GET Done? (kernfs_get) | Extra Refs (create/find) | Total Refs | PUTs (total) | Balanced? | Notes |
|------|-------------|------------------------|---------------------------|------------|--------------|-----------|-------|
| L138 | error (-EINVAL) | NO (before any get) | NONE | 0 | 0 | ✅ | |
| L142 | error (-EINVAL) | NO | NONE | 0 | 0 | ✅ | |
| L147 | success (0) | NO | NONE | 0 | 0 | ✅ | |
| L169 | success (0) | NO (after find, before get) | find (1 ref) | 1 | 1 (L168) | ✅ | find_and_get non‑NULL, mode==0, put on L168 |
| L175 | success (0) | NO | NONE | 0 | 0 | ✅ | update→0, mode==0, no find ref, no create |
| L181 | error (ERR_PTR) | NO (before get) | NONE | 0 | 0 | ✅ | create_dir_ns failed, no ref |
| L199 (update true, find non‑NULL) | error/success | YES (L188) | find (1 ref) | 2 | 2 (L194, L197) | ✅ | find_and_get → ref, extra get, both put |
| **L199 (update false, create success)** | error/success | YES (L188) | **create (1 ref)** | **2** | **1 (L194)** | ❌ **LEAK** | `grp->name && update` false → L197 skipped; ref from `kernfs_create_dir_ns` never dropped |
| L199 (grp->name NULL) | error/success | YES (L188) | NONE | 1 | 1 (L194) | ✅ | kn = kobj->sd, no creation ref |

VERDICT: REAL_BUG

CONFIDENCE: HIGH

`internal_create_group` leaks a reference when it creates a new group directory (update false, or update true but the group didn’t exist). `kernfs_create_dir_ns` returns a node with an initial reference count of 1, then the code takes an extra `kernfs_get(kn)`, but the final `kernfs_put` on the non‑update path is only executed once, leaving the creation reference held forever.
```
