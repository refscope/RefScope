# REAL BUG: drivers/firmware/qcom/qcom_scm.c:2629 qcom_scm_get_waitq_irq()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2629 (return irq_create_fwspec_mapping) | success/irq (value returned) | YES (of_irq_find_parent succeeded, reference taken on device_node) | NO | ❌ LEAK | No of_node_put called; reference held by parent_irq_node is never released. |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2613 (ret) | error       | NO (before of_irq_find_parent) | N/A | ✅ | qcom_scm_call_atomic failed, no ref held |
| L2617 (ret) | error       | NO (before of_irq_find_parent) | N/A | ✅ | qcom_scm_fill_irq_fwspec_params failed, no ref held |
| L2621 (return -ENODEV) | error | NO (of_irq_find_parent returned NULL, no ref given) | N/A | ✅ | NULL check immediately after get; no ref acquired |
| L2629 (return irq_create_fwspec_mapping) | success/irq (value returned) | YES (of_irq_find_parent succeeded, reference taken on device_node) | NO | ❌ LEAK | No of_node_put called; reference held by parent_irq_node is never released. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
of_irq_find_parent takes a reference on the device_node, but no matching of_node_put is called before returning on the success path (line 2629). The fwspec assignment does not transfer ownership; irq_create_fwspec_mapping does not consume the caller’s reference, leading to a permanent leak of the node’s kref.
```
```
