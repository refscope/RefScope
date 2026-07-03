# REAL BUG: net/tipc/node.c:2311 tipc_nl_peer_rm()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L2290-2311 (success) | err_out after `tipc_node_delete` + fallthrough | YES | YES twice (tipc_node_delete at L2295 does put, then tipc_node_put at L2311) | ❌ **EXCESS** | One get, two puts |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2250 | error (return -EINVAL) | NO (before get) | N/A | ✅ | |
| L2255 | error (return err) | NO (before get) | N/A | ✅ | |
| L2263 | error (return -EINVAL) | NO (before get) | N/A | ✅ | |
| L2268 | error (return -EINVAL) | NO (before get) | N/A | ✅ | |
| L2275 | error (return -ENOTSUPP) | NO (before get) | N/A | ✅ | |
| L2280 | error (return -ENXIO) | NO (tipc_node_find returned NULL) | N/A | ✅ | |
| L2286-2288 | goto err_out | YES (tipc_node_find succeeded, state check fails) | YES (tipc_node_put at L2311) | ✅ | single put |
| L2290-2311 (success) | err_out after `tipc_node_delete` + fallthrough | YES | YES twice (tipc_node_delete at L2295 does put, then tipc_node_put at L2311) | ❌ **EXCESS** | One get, two puts |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The success path calls `tipc_node_delete(peer)` (which does a `tipc_node_put`) then falls through to `err_out:` which calls `tipc_node_put(peer)` again – an excess put on the kref acquired by `tipc_node_find`.
```
