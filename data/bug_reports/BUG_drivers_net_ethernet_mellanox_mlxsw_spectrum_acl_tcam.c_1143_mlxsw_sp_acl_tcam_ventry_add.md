# REAL BUG: drivers/net/ethernet/mellanox/mlxsw/spectrum_acl_tcam.c:1143 mlxsw_sp_acl_tcam_ventry_add()

**Confidence**: HIGH | **Counter**: `$->ref_count.refs.counter`

## Reasoning

| goto err_entry_create | error | YES | YES (mlxsw_sp_acl_tcam_vchunk_put) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| after IS_ERR(vchunk) | error | NO (get failed) | N/A | ✅ | |
| return 0 (success) | success | YES | NO | ❌ LEAK | vchunk reference never released |
| goto err_entry_create | error | YES | YES (mlxsw_sp_acl_tcam_vchunk_put) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
mlxsw_sp_acl_tcam_vchunk_get() success path returns without corresponding put; error path does put, but success path leaks reference.
```
