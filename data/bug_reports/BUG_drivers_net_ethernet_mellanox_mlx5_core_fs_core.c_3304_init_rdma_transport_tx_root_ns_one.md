# REAL BUG: drivers/net/ethernet/mellanox/mlx5/core/fs_core.c:3304 init_rdma_transport_tx_root_ns_one()

**Confidence**: HIGH | **Counter**: `root_ns->ns.node.refcount.refs.counter`

## Reasoning

t_idx]` still points to `root_ns`; later cleanup of the array will put again → excess put / double-free. |

## Full Response

```
| Line | Return Type | GET Done? (ns ref) | PUT Done? (cleanup_root_ns) | Balanced? | Notes |
|------|-------------|---------------------|----------------------------|-----------|-------|
| L3283 | error (-ENOMEM) | NO (create_root_ns returned NULL, ns never created) | NO | ✅ | |
| L3293 (goto err) | error via err label | YES (create_root_ns succeeded, ns ref=1; any prior fs_create_prio success may have incremented ns refcount) | YES (cleanup_root_ns called at L3304) | ❌ | `cleanup_root_ns(root_ns)` is called but `steering->rdma_transport_tx_root_ns[vport_idx]` still points to `root_ns`; later cleanup of the array will put again → excess put / double-free. |
| L3301 | success (0) | YES (create_root_ns succeeded, ns ref=1; all fs_create_prio calls succeeded, ns refcount increased) | NO (ownership kept by array) | ✅ (array cleanup will release) | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error path calls cleanup_root_ns() but does not NULL the array pointer, causing a future double-put (excess put) when the steering array is cleaned up.
```
