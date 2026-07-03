# REAL BUG: drivers/gpu/drm/msm/msm_drv.c:954 add_mdp_components()

**Confidence**: HIGH | **Counter**: `intf->kobj.kref.refcount.refs.counter`

## Reasoning

| L958 | return 0 | NO | N/A | ✅ | after loop, no intf held |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L920‑926 | error return | NO (intf not acquired) | N/A | ✅ | `of_node_put(ep_node)` for the parse error, no intf involved |
| L932 | continue | NO | N/A | ✅ | MDP4 special case, intf not touched |
| L940‑942 | continue | NO (intf==NULL) | N/A | ✅ | conditional get, NULL → no reference held |
| L948‑954 (device available) | continue | YES | YES (excess) | ❌ | `drm_of_component_match_add` takes ownership of the reference; subsequent `of_node_put(intf)` puts an already‑transferred ref → excess put |
| L954 (device not available) | continue | YES | YES | ✅ | not added to match, so the put correctly releases the caller’s own ref |
| L958 | return 0 | NO | N/A | ✅ | after loop, no intf held |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`drm_of_component_match_add` stores the node and will release it via `component_release_of`; calling `of_node_put(intf)` afterwards over-releases the reference.
```
