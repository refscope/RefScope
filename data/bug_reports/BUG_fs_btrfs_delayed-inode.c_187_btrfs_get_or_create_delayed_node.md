# REAL BUG: fs/btrfs/delayed-inode.c:187 btrfs_get_or_create_delayed_node()

**Confidence**: HIGH | **Counter**: `$->ref_dir.dir.untracked.refs.counter`

## Reasoning

| L179 | return node (success) | YES (references held by tree/inode) | N/A (caller will later put) | ✅ | Node correctly stored; references accounted for. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L148 | success (return early) | YES (btrfs_get_delayed_node took ref) | N/A (caller will release) | ✅ | Returning existing node with proper reference. |
| L152 | error (ENOMEM) | NO (alloc failed, no node) | N/A | ✅ | NULL node, no refcount held. |
| L163 | goto cleanup (xa_reserve -ENOMEM) | YES (refcount_set to 2 + tracker allocs) | NO (refs not dropped before free) | ❌ LEAK | cleanup label frees node without decrementing node->refs. |
| L170 | goto cleanup (xa_load found existing) | YES (refcount_set to 2 + tracker allocs) | NO | ❌ LEAK | Same as above; node freed with refs still at 2. |
| L179 | return node (success) | YES (references held by tree/inode) | N/A (caller will later put) | ✅ | Node correctly stored; references accounted for. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Refcount of the newly allocated node (node->refs) is set to 2 but never decremented on the error paths that go to cleanup and free the node, causing a refcount leak before the memory is reclaimed.
```
