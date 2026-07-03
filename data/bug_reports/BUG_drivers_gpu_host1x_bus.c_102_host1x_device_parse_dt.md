# REAL BUG: drivers/gpu/host1x/bus.c:102 host1x_device_parse_dt()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L97  | error (return err) | YES (host1x_subdev_add() called, unconditional GET per contract) | NO  | ❌ LEAK | error return after host1x_subdev_add fails, no matching put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L101 | success (return 0) | YES (host1x_subdev_add unconditional get for each successful subdev) | N/A (refs held for subdevice lifetime) | ✅ | normal operation; refs will be released on device removal |
| L97  | error (return err) | YES (host1x_subdev_add() called, unconditional GET per contract) | NO  | ❌ LEAK | error return after host1x_subdev_add fails, no matching put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

host1x_subdev_add is an unconditional GET according to the contract. On the error return at line 97, the reference it acquired is not released, causing a kref leak. The for_each_child_of_node_scoped macro handles its own np references properly.
```
