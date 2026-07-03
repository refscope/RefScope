# REAL BUG: fs/configfs/dir.c:1789 configfs_register_group()

**Confidence**: MEDIUM | **Counter**: `$->cg_item.ci_kref.refcount.refs.counter`

## Reasoning

| L1772 (success) | return 0 | YES (assumed, ref held by parent) | NO (ref transferred to parent) | ✅ | Parent’s reference will be dropped later |

## Full Response

```
| Line | Return Type | GET Done? (link_group) | PUT Done? (unlink_group) | Balanced? | Notes |
|------|-------------|------------------------|--------------------------|-----------|-------|
| L1758 (frag alloc fail) | error return -ENOMEM | NO (before link_group) | N/A | ✅ | |
| L1766 (goto err_out) | error return ret | **UNCERTAIN** – link_group() called at ~L1770 with **no return check**; if it succeeded, YES; if it failed/silently skipped ref, NO | YES at L1789 | ❌ if link_group did **not** take a ref → excess put | Warning points to excess put at L1789, strongly suggesting the GET didn’t happen on this path |
| L1772 (success) | return 0 | YES (assumed, ref held by parent) | NO (ref transferred to parent) | ✅ | Parent’s reference will be dropped later |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
configfs_register_group() unconditionally calls unlink_group() on the error path after a potentially unsuccessful link_group() (no return check), causing an extra kref_put when the reference was never taken.
```
