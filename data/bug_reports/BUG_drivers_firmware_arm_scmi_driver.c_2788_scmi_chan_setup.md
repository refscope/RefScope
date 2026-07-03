# REAL BUG: drivers/firmware/arm_scmi/driver.c:2788 scmi_chan_setup()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2781 | success (0) | YES (L2748 of_node_get) | NO | ❌ LEAK | No of_node_put; success path returns without releasing reference. No visible ownership transfer cleanup in provided context. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2725 | error (-EINVAL) | NO (before get) | N/A | ✅ | |
| L2731 | error (-ENOMEM) | NO (before get) | N/A | ✅ | |
| L2746 | error (-EINVAL) | NO (before get) | N/A | ✅ | |
| L2757 | error (ret) | YES (L2748 of_node_get) | YES (L2754 of_node_put) | ✅ | |
| L2777 | error (ret) | YES (L2748 of_node_get) | YES (L2773 of_node_put) | ✅ | tdev != NULL, so put happens |
| L2781 | success (0) | YES (L2748 of_node_get) | NO | ❌ LEAK | No of_node_put; success path returns without releasing reference. No visible ownership transfer cleanup in provided context. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The success path at L2781 increments the node refcount via of_node_get (unconditional) but never calls of_node_put. While the reference may be intended for the channel lifetime, the provided source does not show the matching put in any teardown function, and the default burden of proof for ownership transfer is not met.
```
