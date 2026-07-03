# REAL BUG: drivers/infiniband/hw/irdma/cm.c:3083 irdma_cm_reject()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L3083 | return ret (mpa reject failure) | YES | NO | ❌ LEAK | node state set to CLOSED but irdma_rem_ref_cm_node missing |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3055 | return 0 (tcp_cntxt.client) | NO (before any get) | N/A | ✅ | |
| L3063 | return 0 (passive_state == IRDMA_SEND_RESET_EVENT) | YES (node reference) | YES (irdma_rem_ref_cm_node) | ✅ | releases reference |
| L3068 | return 0 (state LISTENER_DESTROYED) | YES | YES | ✅ | |
| L3073 | return 0 (mpa reject success) | YES | NO | ⚠️ (normal) | node stays active, reference intentionally retained |
| L3083 | return ret (mpa reject failure) | YES | NO | ❌ LEAK | node state set to CLOSED but irdma_rem_ref_cm_node missing |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After setting cm_node->state to IRDMA_CM_STATE_CLOSED, the error path at L3083 returns without calling irdma_rem_ref_cm_node, leaking the node's reference.
```
```
