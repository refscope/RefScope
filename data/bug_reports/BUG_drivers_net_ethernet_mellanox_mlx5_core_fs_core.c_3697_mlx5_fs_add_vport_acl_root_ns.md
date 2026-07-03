# REAL BUG: drivers/net/ethernet/mellanox/mlx5/core/fs_core.c:3697 mlx5_fs_add_vport_acl_root_ns()

**Confidence**: HIGH | **Counter**: `vport_ns->root_ns->ns.node.refcount.refs.counter`

## Reasoning

| L3690 (goto cleanup_root_ns) | error (various) | YES (fs_create_prio succeeded) | YES  | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3657 | error (-EINVAL) | NO (before get) | N/A  | ✅ | |
| L3664 | error (-EINVAL) | NO (before get) | N/A  | ✅ | |
| L3668 | error (-EEXIST) | NO (before get) | N/A  | ✅ | |
| L3672 | error (-ENOMEM) | NO (before get) | N/A  | ✅ | |
| L3677 (goto kfree_vport_ns) | error (-ENOMEM) | NO (create_root_ns failed) | NO (cleanup not called) | ✅ | No ref on ns.node yet |
| L3684 (goto cleanup_root_ns) | error (PTR_ERR) | **NO** (IS_ERR guard: fs_create_prio failed) | **YES** (cleanup_root_ns called) | ❌ **excess put** | GET not done, PUT done |
| L3690 (goto cleanup_root_ns) | error (various) | YES (fs_create_prio succeeded) | YES  | ✅ | |
| L3691 | success 0 | YES (fs_create_prio succeeded) | NO (ownership transferred to xarray) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
fs_create_prio failure path (L3684) unconditionally calls cleanup_root_ns, but the IS_ERR guard means the get never happened → excess put on root_ns->ns.node refcount.
```
