# REAL BUG: kernel/audit_tree.c:873 audit_add_tree_rule()

**Confidence**: HIGH | **Counter**: `$->count.refs.counter`

## Reasoning

t from 1 to 2. The error handler `Err:` (L868‑873) removes the tree from its lists and calls `put_tree()` only once, decrementing to 1 before returning. The tree object is never freed, and its final reference is leaked. The other error paths (before `get_tree`) correctly free the single reference.

## Full Response

```
| Line | Return Type | GET Done? (get_tree) | PUT Done? (put_tree) | Balanced? | Notes |
|------|-------------|----------------------|----------------------|-----------|-------|
| L819 | return 0 | NO (before get_tree) | put_tree(seed) for original | ✅ | Tree already exists, seed freed. |
| L831 | goto Err (audit_launch_prune fail) | NO (get_tree not called) | YES (L872 put_tree) | ✅ | Removes from lists + frees original ref. |
| L836 | goto Err (kern_path fail) | NO | YES (L872) | ✅ | |
| L841 | goto Err (collect_paths IS_ERR) | NO | YES (L872) | ✅ | |
| L856 | goto Err (tag_mounts fail) | **YES (L844)** | YES (L872 put_tree once) | ❌ **LEAK** | Ref = original+1, only one put. Original ref from list is dropped but not released to zero. Tree leaks. |
| L862 | return -ENOENT | YES (L844) | YES (L861) | ✅ | Extra get dropped; original still held by tree_list. |
| L867 | return 0 | YES (L844) | YES (L865) | ✅ | Extra get dropped; original transferred to rule->tree. |

**Reasoning**: On the `tag_mounts` failure path (L856), `get_tree()` has already incremented the tree’s refcount from 1 to 2. The error handler `Err:` (L868‑873) removes the tree from its lists and calls `put_tree()` only once, decrementing to 1 before returning. The tree object is never freed, and its final reference is leaked. The other error paths (before `get_tree`) correctly free the single reference.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
