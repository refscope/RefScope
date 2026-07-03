# REAL BUG: fs/ocfs2/cluster/nodemanager.c:860 init_o2nm()

**Confidence**: HIGH | **Counter**: `o2nm_cluster_group.cs_subsys.su_group.cg_item.ci_kref.refcount.refs.counter`

## Reasoning

| L854 (goto out) | success (o2cb_sys_init success) | YES (config_group_init) | NO (no immediate put) | ⚠️ deferred balance (module exit will unregister) | Success path keeps subsystem registered; the initial ref is held until module cleanup. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L838 (goto out_o2hb) | error (o2net_init fail) | NO (before config_group_init) | N/A | ✅ | No config_group operations yet |
| L842 (goto out_o2net) | error (callbacks fail) | NO | N/A | ✅ | Before config_group_init |
| L848 (goto out_callbacks) | error (configfs_register_subsystem fail) | YES (config_group_init at L844) | NO (out_callbacks has no configfs_unregister_subsystem) | ❌ LEAK | Initial kref from config_group_init is never released on this error path |
| L854 (goto out) | success (o2cb_sys_init success) | YES (config_group_init) | NO (no immediate put) | ⚠️ deferred balance (module exit will unregister) | Success path keeps subsystem registered; the initial ref is held until module cleanup. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
config_group_init sets a kref to 1; the error path after configfs_register_subsystem failure jumps to out_callbacks which lacks configfs_unregister_subsystem, leaking that initial reference.
```
