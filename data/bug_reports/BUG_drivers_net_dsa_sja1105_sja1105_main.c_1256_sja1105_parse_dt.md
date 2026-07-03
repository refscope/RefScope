# REAL BUG: drivers/net/dsa/sja1105/sja1105_main.c:1256 sja1105_parse_dt()

**Confidence**: HIGH | **Counter**: `ports_node->kobj.kref.refcount.refs.counter`

## Reasoning

put(ports_node) called) | ❌ EXCESS PUT | **Warning** at the `of_node_put` confirms refcount already zero at this point; implies another put occurred earlier, likely inside `sja1105_parse_ports_node()` (e.g., error path or unconditional consumption of the reference). One get, two puts → real bug. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1250 (return -ENODEV) | error (ports_node NULL) | NO (both of_get_child_by_name returned NULL) | N/A | ✅ | No reference taken, no put needed |
| L1254–L1256 (rc path) | success/error return rc | YES (one of the of_get_child_by_name calls succeeded, held ref) | YES (of_node_put(ports_node) called) | ❌ EXCESS PUT | **Warning** at the `of_node_put` confirms refcount already zero at this point; implies another put occurred earlier, likely inside `sja1105_parse_ports_node()` (e.g., error path or unconditional consumption of the reference). One get, two puts → real bug. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The reference obtained by `of_get_child_by_name` is released twice: once somewhere inside `sja1105_parse_ports_node()` (or its error handling) and again at line 1256, causing an excess put and refcount underflow. Fix: either remove the caller's `of_node_put` if callee always consumes the reference, or fix the callee to not drop it.
```
