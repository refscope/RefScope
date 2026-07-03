# REAL BUG: drivers/net/ethernet/mellanox/mlxsw/spectrum_router.c:7128 mlxsw_sp_nexthop6_group_create()

**Confidence**: HIGH | **Counter**: `$->router.num_groups.refs.counter`

## Reasoning

| L7120 (return nh_grp) | success | YES | NO (caller will put) | ✅ | Group returned to caller, normal lifecycle |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L7098 (return ERR_PTR(-ENOMEM)) | error | NO | N/A | ✅ | Before any get |
| L7104 (goto err_nexthop_group_vr_ht_init → return ERR_PTR(err)) | error | NO | N/A | ✅ | rhashtable_init failed; no get yet |
| L7112 (goto err_nexthop_group_info_init → return ERR_PTR(err)) | error | **YES** (unconditional) | **NO** (skips `_fini`) | ❌ LEAK | `mlxsw_sp_nexthop6_group_info_init` got ref, but error path does not put |
| L7116 (goto err_nexthop_group_insert → return ERR_PTR(err)) | error | YES | YES (via `_fini`) | ✅ | Insert failed; `_fini` correctly releases |
| L7120 (return nh_grp) | success | YES | NO (caller will put) | ✅ | Group returned to caller, normal lifecycle |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`mlxsw_sp_nexthop6_group_info_init` unconditionally increments the counter (`mlxsw_sp_nexthop_group_inc`). When it fails (L7110 `err`), the `goto err_nexthop_group_info_init` skips `mlxsw_sp_nexthop6_group_info_fini`, leaking the reference. The missing put is at L7112: the label should first call `fini` before destroying the hashtable.
```
