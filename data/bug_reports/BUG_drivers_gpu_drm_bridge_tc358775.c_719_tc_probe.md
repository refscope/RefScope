# REAL BUG: drivers/gpu/drm/bridge/tc358775.c:719 tc_probe()

**Confidence**: HIGH | **Counter**: `$->host_node->kobj.kref.refcount.refs.counter`

## Reasoning

| L118 | success     | YES | NO (will be released in remove()) | ✅ | success path, ownership transferred, cleanup via device removal |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L13  | error       | NO (before get) | N/A  | ✅ | before tc_probe_bridge_endpoint, no host_node ref |
| L19  | error       | NO (if tc_probe_bridge_endpoint fails, it cleans up internally) | N/A  | ✅ | function contract: on error, no ref stored |
| L24  | error       | YES (host_node acquired and stored in tc) | NO   | ❌ LEAK | after tc_probe_bridge_endpoint success; refclk error returns without of_node_put |
| L30  | error       | YES | NO   | ❌ LEAK | sd_gpio error |
| L37  | error       | YES | NO   | ❌ LEAK | reset_gpio error |
| L49  | error       | YES | NO   | ❌ LEAK | regmap init error |
| L60  | error       | YES | NO   | ❌ LEAK | invalid hpd_pin |
| L69  | error       | YES | NO   | ❌ LEAK | irq request failure |
| L76  | error       | YES | NO   | ❌ LEAK | regmap_read failure |
| L81  | error       | YES | NO   | ❌ LEAK | invalid device ID |
| L103 | error       | YES | NO   | ❌ LEAK | tc_aux_link_setup failure |
| L114 | error       | YES | NO   | ❌ LEAK | DSI host attach failure calls drm_bridge_remove but not of_node_put |
| L118 | success     | YES | NO (will be released in remove()) | ✅ | success path, ownership transferred, cleanup via device removal |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`tc_probe_bridge_endpoint` unconditionally obtains a `host_node` reference (via `of_graph_get_remote_node`) and stores it in `tc`. After that call succeeds, all error returns in `tc_probe` (L24–L114) lack a corresponding `of_node_put`, leaking the kref on `host_node`. The success path handles cleanup only in `remove()`.
```
