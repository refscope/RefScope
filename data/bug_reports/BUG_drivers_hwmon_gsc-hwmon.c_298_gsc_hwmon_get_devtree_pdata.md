# REAL BUG: drivers/hwmon/gsc-hwmon.c:298 gsc_hwmon_get_devtree_pdata()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L291 | success     | YES (parent) | NO (parent) | ❌ LEAK | normal success return; parent ref never released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L245 | error       | NO (before get) | N/A  | ✅ | nchannels==0 check before of_node_get |
| L249 | error       | NO (before get) | N/A  | ✅ | pdata allocation failure before get |
| L258 | error       | YES (parent) | NO (parent) | ❌ LEAK | **of_node_get at L253; fan error branch puts fan only** |
| L267 | error       | YES (parent) | NO (parent) | ❌ LEAK | loop: channel label missing; parent ref never released |
| L271 | error       | YES (parent) | NO (parent) | ❌ LEAK | loop: channel reg missing |
| L275 | error       | YES (parent) | NO (parent) | ❌ LEAK | loop: channel mode missing |
| L279 | error       | YES (parent) | NO (parent) | ❌ LEAK | loop: channel mode out of range |
| L291 | success     | YES (parent) | NO (parent) | ❌ LEAK | normal success return; parent ref never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get(dev->parent->of_node)` at L253 acquires a reference that is never released on any subsequent path (errors and success), causing a leak of the parent device_node’s kref.
```
