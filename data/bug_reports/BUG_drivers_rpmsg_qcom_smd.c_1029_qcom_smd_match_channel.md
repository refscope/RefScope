# REAL BUG: drivers/rpmsg/qcom_smd.c:1029 qcom_smd_match_channel()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1030 (return NULL) | no match | NO (last child ref was released by loop termination) | N/A | YES | Loop correctly releases all references; NULL returned with no ref held. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1028 (return child) | success (match) | YES (of_get_next_available_child incremented refcount) | YES (implicit scope cleanup at loop end ~L1029 calls of_node_put(child)) | NO | Cleanup puts the child’s kref before the function returns; caller will later put it again, causing an excess put (double-decrement). |
| L1030 (return NULL) | no match | NO (last child ref was released by loop termination) | N/A | YES | Loop correctly releases all references; NULL returned with no ref held. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The for_each_available_child_of_node loop (recent kernels) uses automatic cleanup (`__free(device_node)`) that calls of_node_put(child) at the closing brace. Returning child inside the loop triggers this cleanup, prematurely dropping the reference before the caller can take ownership, leading to an “excess put” when the caller later releases the returned node.
```
