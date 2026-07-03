# REAL BUG: drivers/net/ethernet/mellanox/mlx5/core/fs_core.c:3273 init_rdma_transport_rx_root_ns_one()

**Confidence**: HIGH | **Counter**: `root_ns->ns.node.refcount.refs.counter`

## Reasoning

ing array. The caller will later attempt to clean up the array entry (e.g., in a rollback path), which will also put the same root_ns, causing an `refcount excess put`. The error path should not destroy the root_ns; the caller owns the reference and will release it. This is a clear double‑put bug.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L3252 (create_root_ns fails) | error (-ENOMEM) | NO (create failed) | N/A | ✅ | no object allocated |
| ~L3264 (IS_ERR, inside loop) -> goto err | error | YES (from create_root_ns + all successful fs_create_prio) | YES (via cleanup_root_ns at L3273) | ❌ | cleanup_root_ns puts root_ns, but root_ns pointer still stored in steering array → double put with later cleanup |
| ~L3270 (success) | 0 (success) | YES (from create_root_ns + all prios) | NO (PUT done externally later) | ✅ | root_ns owned by steering, cleaned up on device removal |

**Reasoning**: The function stores `root_ns` in `steering->rdma_transport_rx_root_ns[vport_idx]` *before* the loop. On error, it calls `cleanup_root_ns(root_ns)` which drops the reference, but the pointer remains in the steering array. The caller will later attempt to clean up the array entry (e.g., in a rollback path), which will also put the same root_ns, causing an `refcount excess put`. The error path should not destroy the root_ns; the caller owns the reference and will release it. This is a clear double‑put bug.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
cleanup_root_ns at L3273 erroneously releases root_ns while it remains stored in steering->rdma_transport_rx_root_ns[vport_idx], leading to a double put when the caller later cleans up.
```
