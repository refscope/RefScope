# REAL BUG: drivers/media/i2c/max9286.c:1539 max9286_parse_dt()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1535 | success (0)     | YES (of_node_get at L1403) | NO | ❌ LEAK | Normal return; no of_node_put(dev->of_node). |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1407 | error (-EINVAL) | YES (of_node_get at L1403) | NO (dev->of_node not put) | ❌ LEAK | Bail out after failing to find i2c-mux; get already executed. |
| L1453 | error (ret) | YES (of_node_get at L1403) | NO | ❌ LEAK | v4l2 endpoint parse failure; returns after putting local endpoint node, but dev->of_node get not released. |
| L1501 | error (-EINVAL) | YES (of_node_get at L1403) | NO | ❌ LEAK | Invalid bus-width property. |
| L1516 | error (-EINVAL) | YES (of_node_get at L1403) | NO | ❌ LEAK | Invalid i2c-remote-bus-hz property. |
| L1535 | success (0)     | YES (of_node_get at L1403) | NO | ❌ LEAK | Normal return; no of_node_put(dev->of_node). |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get(dev->of_node)` at L1403 increments the refcount on dev->of_node, but no matching `of_node_put()` exists in the function (and `of_find_node_by_name` internally balances its own get/put, so the explicit get is superfluous and leaks a reference on every return path).
```
