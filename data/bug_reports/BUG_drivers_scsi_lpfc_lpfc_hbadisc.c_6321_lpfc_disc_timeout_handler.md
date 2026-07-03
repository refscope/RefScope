# REAL BUG: drivers/scsi/lpfc/lpfc_hbadisc.c:6321 lpfc_disc_timeout_handler()

**Confidence**: MEDIUM | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

| All other switch cases (`LPFC_FDISC`, `LPFC_FLOGI`, etc.) → break → second switch → final return | final return | NO | NO (no ndlp touched) | N/A | No ndlp operations. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L6101 | early return (if !test_and_clear_bit) | NO | NO | N/A | No ndlp operations. |
| L6128 (`return` inside `LPFC_LOCAL_CFG_LINK` after `port_state != LPFC_FLOGI`) | return within switch case | NO (no explicit get in this function) | YES (via `lpfc_drop_node` or `lpfc_unreg_rpi` in the loop) | ❌ PUT without GET in function scope | Nodes may still be in list after `lpfc_unreg_rpi` put, risking refcount underflow if list reference is the last one. |
| L6155 (break from `LPFC_LOCAL_CFG_LINK` when `port_state == LPFC_FLOGI`, then fall through to second switch and final return) | final return | NO | YES (same loop puts as above) | ❌ PUT without GET in function scope | Same risk: `lpfc_unreg_rpi` put may drop refcount to zero while node remains on list, then later list cleanup (e.g., `lpfc_disc_flush_list` in other paths) could trigger excess put, or immediate underflow if refcount was already 1. |
| All other switch cases (`LPFC_FDISC`, `LPFC_FLOGI`, etc.) → break → second switch → final return | final return | NO | NO (no ndlp touched) | N/A | No ndlp operations. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

In `lpfc_disc_timeout_handler`, the `LPFC_LOCAL_CFG_LINK` case iterates the `fc_nodes` list and for non-fabric NPR nodes without `NLP_NPR_ADISC` calls `lpfc_unreg_rpi`, which performs a `lpfc_nlp_put`. The node remains on the list after this put. If the node’s only remaining reference is the list’s reference, the `put` will drop the refcount to zero while the node is still linked, leading to a use-after-free when the list later releases its reference (or an immediate refcount underflow warning). The lack of a matching get in this function combined with the unconditional put on a still-listed node constitutes an excess put. The contracts confirm `lpfc_unreg_rpi` contains a put, and the code does not remove the node or ensure an additional reference exists, making this a real refcounting bug.
```
