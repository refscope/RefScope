# REAL BUG: drivers/scsi/lpfc/lpfc_hbadisc.c:4812 lpfc_nlp_state_cleanup()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

recursive `lpfc_nlp_unreg_node` triggered by `lpfc_nlp_set_state` → UNMAPPED | ❌ | Recursive `lpfc_nlp_set_state` → `lpfc_nlp_state_cleanup(old=MAPPED,new=UNMAPPED)` calls `lpfc_nlp_unreg_node` again, causing a second put without a matching get, leading to a use-after-free / refcount underflow. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 4773 | early return (ADISC) | NO | NO | ✅ | No ndlp kref operations in this function (callee may be opaque but not the target) |
| 4814 (implicit return via path not entering if block 4806) | normal exit, no set_state after reg_node | YES (if reg_node called for new_state) | YES (if unreg_node called for old_state) | ✅ | Standard state transition; gets/puts balance correctly per old/new state rules |
| 4814 (implicit return via path entering if block 4806 and calling `lpfc_nlp_set_state` at line 4812) | normal exit after recursive state change | YES (from reg_node at 4798) + potential get inside recursive cleanup | YES (from unreg_node at 4793 if condition met) + PUT from recursive `lpfc_nlp_unreg_node` triggered by `lpfc_nlp_set_state` → UNMAPPED | ❌ | Recursive `lpfc_nlp_set_state` → `lpfc_nlp_state_cleanup(old=MAPPED,new=UNMAPPED)` calls `lpfc_nlp_unreg_node` again, causing a second put without a matching get, leading to a use-after-free / refcount underflow. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

The call `lpfc_nlp_set_state(vport, ndlp, NLP_STE_UNMAPPED_NODE)` at line 4812 (inside a `lpfc_nlp_state_cleanup()` transition to MAPPED) triggers a recursive `lpfc_nlp_state_cleanup()` with old_state=MAPPED, new_state=UNMAPPED. That recursive invocation will again call `lpfc_nlp_unreg_node()` for the old_state MAPPED, which does a kref_put. The original path already called `lpfc_nlp_reg_node()` (get) and possibly `lpfc_nlp_unreg_node()` (put) for the outer state transition. The extra put from the recursive unreg_node leads to a double-put of the ndlp kref, and when the ndlp still has a reference from the outer registration, it can underflow and free the node prematurely. This is a classic refcount bug caused by inducting a state change from within the cleanup handler of another state change.
```
