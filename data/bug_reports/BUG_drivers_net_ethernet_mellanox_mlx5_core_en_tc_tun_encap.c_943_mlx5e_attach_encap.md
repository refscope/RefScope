# REAL BUG: drivers/net/ethernet/mellanox/mlx5/core/en/tc_tun_encap.c:943 mlx5e_attach_encap()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| **out_err_init (L~943 return after kfree)** | **error** | **YES** | **NO** | **❌ LEAK** | **refcount was 1, never decremented before free → inconsistent refcounting** |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L843 (return -EOPNOTSUPP) | error | NO (before any get) | N/A | ✅ | key.tc_tunnel NULL early return |
| L859 (goto out_err after is_duplicated) | error | YES (from mlx5e_encap_get) | YES (out_err puts) | ✅ | get then put |
| L861 (goto attach_flow) | success path | YES (get) | NO (ownership transferred) | ✅ | reference transferred to flow |
| L865 (goto out_err after kzalloc_obj fail, e=NULL) | error | NO | N/A | ✅ | e is NULL → no put |
| L876 (goto out_err_init after tun_info alloc fail) | error | YES (initial refcount=1) | NO (kfree directly, **no put**) | ❌ LEAK | refcount set to 1, never decremented |
| L882 (goto out_err_init after mlx5e_tc_tun_init_encap_attr fail) | error | YES (initial refcount=1) | NO (kfree directly, **no put**) | ❌ LEAK | same |
| L892 (goto out_err after header creation error, after hash_add_rcu) | error | YES (creation ref) | YES (out_err puts) | ✅ | hash_add done → put releases |
| L898 (goto out_err after mlx5e_attach_encap_route fail) | error | YES (from get/creation) | YES (out_err puts) | ✅ | |
| L904 (goto out_err after int port tunnel err, non‑EOPNOTSUPP) | error | YES | YES | ✅ | |
| L911 (success return after list_add) | success | YES (get/creation) | NO (ownership transfer) | ✅ | reference now owned by flow, no leak |
| out_err (L~938 return after put) | error | YES | YES | ✅ | balanced |
| **out_err_init (L~943 return after kfree)** | **error** | **YES** | **NO** | **❌ LEAK** | **refcount was 1, never decremented before free → inconsistent refcounting** |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The error path at `out_err_init` incorrectly calls `kfree(e)` instead of `mlx5e_encap_put_locked(priv, e)`, leaving the newly created entry’s reference count at 1 while freeing the memory, which is a clear refcounting inconsistency.
```
