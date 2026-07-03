# REAL BUG: drivers/gpu/host1x/bus.c:69 host1x_subdev_add()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L72 | success (return 0) | YES | NO (transferred to list) | ✅ | Reference remains in subdev->np, cleaned on device teardown |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L44 | error (-ENOMEM) | NO (before get) | N/A | ✅ | |
| L69 | error (return err) | YES (of_node_get at L48) | NO | ❌ LEAK | Missing of_node_put(subdev->np); no cleanup for list entry |
| L72 | success (return 0) | YES | NO (transferred to list) | ✅ | Reference remains in subdev->np, cleaned on device teardown |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get(np)` at line 48 acquires a reference that is not released on the `return err` path at line 69 when recursive `host1x_subdev_add` fails.
```
