# REAL BUG: drivers/net/dsa/hirschmann/hellcreek_ptp.c:397 hellcreek_led_setup()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L393→L397 | success (ret=0) | YES (L310) | NO | ❌ LEAK | fall through out: only puts leds, then returns |

## Full Response

```
| Line | Return Type | GET Done? (dev->of_node) | PUT Done? (dev->of_node) | Balanced? | Notes |
|------|-------------|--------------------------|--------------------------|-----------|-------|
| L315 | error (return ret) | YES (L310 of_node_get) | NO | ❌ LEAK | leds==NULL path, no of_node_put |
| L323 | goto out (error) | YES (L310) | NO | ❌ LEAK | first child missing, out: only puts leds |
| L349 | goto out (error) | YES (L310) | NO | ❌ LEAK | second child missing, out: only puts leds |
| L382 | goto out (error) | YES (L310) | NO | ❌ LEAK | first led register fail, out: only puts leds |
| L391 | goto out (error) | YES (L310) | NO | ❌ LEAK | second led register fail, out: only puts leds |
| L393→L397 | success (ret=0) | YES (L310) | NO | ❌ LEAK | fall through out: only puts leds, then returns |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get(hellcreek->dev->of_node)` at line 310 acquires a reference that is never released. Every return path after this call (including error and success) lacks a matching `of_node_put`, causing a refcount leak on the device node.
```
