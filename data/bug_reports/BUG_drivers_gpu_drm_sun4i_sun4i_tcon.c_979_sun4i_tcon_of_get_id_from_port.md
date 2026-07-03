# REAL BUG: drivers/gpu/drm/sun4i/sun4i_tcon.c:979 sun4i_tcon_of_get_id_from_port()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L979 | int         | YES (on `remote` node each time `of_graph_get_remote_endpoint` succeeds) | NO | ❌ LEAK | No `of_node_put(remote)` inside loop; `remote` reference leaked every iteration that finds an endpoint |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L979 | int         | YES (on `remote` node each time `of_graph_get_remote_endpoint` succeeds) | NO | ❌ LEAK | No `of_node_put(remote)` inside loop; `remote` reference leaked every iteration that finds an endpoint |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_graph_get_remote_endpoint()` acquires a reference to `remote` on every successful call, but the function never releases it with `of_node_put(remote)`; this causes a reference count leak on every loop iteration where a remote endpoint is found.
```
