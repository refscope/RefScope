# REAL BUG: drivers/gpu/drm/display/drm_dp_mst_topology.c:2539 drm_dp_mst_handle_conn_stat()

**Confidence**: HIGH | **Counter**: `$->topology_kref.refcount.refs.counter`

## Reasoning

| L2538 (all other paths reaching out normally) | normal return (dowork variable) | YES | YES (once at L2538) | ✅ | single put matches the get; balanced |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2486 | error return (port == NULL) | NO | N/A | ✅ | drm_dp_get_port returned NULL, no reference held |
| L2498 (goto out after unlink_port) | normal return (dowork true) | YES (via drm_dp_get_port) | YES (unlink_port put at L2495, then another put at L2538) | ❌ EXCESS | drm_dp_mst_topology_unlink_port already decrements topology_kref (contract: unconditional put). The final put_port at L2538 releases the same reference again → double-put, refcount underflow. |
| L2538 (all other paths reaching out normally) | normal return (dowork variable) | YES | YES (once at L2538) | ✅ | single put matches the get; balanced |

**PRE-VERDICT CHECKLIST**  
- “Held for device lifetime”? Not applicable.  
- “Ownership transferred”? No – port is not handed off to a long-lived structure that will later release it.  
- Unconditional get? The get succeeded, so the reference is held.  
- goto out between GET and PUT? Yes – the `goto out` at L2498 after `unlink_port` (a put) leads to a second put at `out` → double put.  

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The `goto out` after `drm_dp_mst_topology_unlink_port()` adds an extra `topology_kref` put, causing a refcount underflow on the port. The unlink already releases the reference, so the subsequent `put_port` is excessive.
```
