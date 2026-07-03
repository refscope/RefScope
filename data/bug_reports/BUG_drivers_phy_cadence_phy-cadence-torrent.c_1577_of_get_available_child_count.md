# REAL BUG: drivers/phy/cadence/phy-cadence-torrent.c:1577 of_get_available_child_count()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1577 | success     | YES (on each child node via of_get_next_available_child) | NO (no of_node_put on any child) | ❌ LEAK | The loop iterates children, taking a reference on each, but never releases them. This is a refcount leak. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1577 | success     | YES (on each child node via of_get_next_available_child) | NO (no of_node_put on any child) | ❌ LEAK | The loop iterates children, taking a reference on each, but never releases them. This is a refcount leak. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The function leaks a reference on every available child node because for_each_available_child_of_node does not automatically put the previous child; after the loop child holds the last node’s reference, and no of_node_put is called. The reported “excess put” likely stems from smatch misinterpreting the leak as an implied put at scope exit, but the core defect is a missing release.
```
