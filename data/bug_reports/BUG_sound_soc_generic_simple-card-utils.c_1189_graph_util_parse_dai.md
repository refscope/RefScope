# REAL BUG: sound/soc/generic/simple-card-utils.c:1189 graph_util_parse_dai()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| else branch fall‑through to L1168‑L1172 | success (no dai found)           | YES       | NO        | ❌ LEAK   | `node` obtained from `of_graph_get_port_parent()` is never stored in `dlc->of_node` (that gets `resolved_dlc.of_node` instead) and is **not** released on the success path |

## Full Response

```
```
| Line | Return Type                              | GET Done? | PUT Done? | Balanced? | Notes |
|------|------------------------------------------|-----------|-----------|-----------|-------|
| L1132 | early return (ep is NULL)                | NO (before get) | N/A       | ✅        |       |
| L1148 | error (dai_args == NULL in `if (dai)`)   | YES       | YES (ret<0 triggers put) | ✅        |       |
| dai branch fall‑through to L1168‑L1172 | success (dai found)               | YES       | NO        | ✅        | Reference transferred to `dlc->of_node`, caller responsible for release |
| L1155 | error (`snd_soc_get_dlc` returns < 0)     | YES       | YES (ret<0 triggers put) | ✅        |       |
| L1161 | error (`devm_kstrdup_const` returns NULL) | YES       | YES (ret<0 triggers put) | ✅        |       |
| else branch fall‑through to L1168‑L1172 | success (no dai found)           | YES       | NO        | ❌ LEAK   | `node` obtained from `of_graph_get_port_parent()` is never stored in `dlc->of_node` (that gets `resolved_dlc.of_node` instead) and is **not** released on the success path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_graph_get_port_parent()` returns a reference that is leaked in the `else` branch success path; the node is neither stored in `dlc->of_node` nor put before returning. The error paths correctly release it, but the success path does not.
```
