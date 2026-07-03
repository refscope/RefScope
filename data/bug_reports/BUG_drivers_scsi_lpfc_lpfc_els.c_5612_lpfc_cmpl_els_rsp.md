# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:5612 lpfc_cmpl_els_rsp()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

e list) → then release | release | None extra | **lpfc_drop_node does a PUT that releases the last reference** | ❌ **Excess put** – refcount underflow at final put (line 5612) | **BUG**: lpfc_drop_node drops the last reference, then the unconditional final lpfc_nlp_put(ndlp) causes underflow. |

## Full Response

```
## Path Table

| Line(s) | Return Type | GET Done? | PUT before final (line 5612)? | Final PUT Balanced? | Notes |
|---------|-------------|-----------|-------------------------------|----------------------|-------|
| Early !vport → goto release | release (one exit) | No extra gets | None | ✅ | ndlp may be NULL; lpfc_nlp_put(NULL) is safe. |
| ndlp NULL or link down → goto out → release | release | No extra gets | None | ✅ | ndlp may be NULL; if not NULL, single put is fine. |
| mbox && !PT2PT, ulp_status==0, ACC_REGLOGIN: lpfc_unreg_rpi succeeds, goto out_free_mbox → release | release | Possibly via unreg_rpi internals (balanced with its own put) | unreg_rpi may do a put for its own reference | ✅ | Callback reference still held; final put releases it. |
| mbox && !PT2PT, ACC_REGLOGIN: get ndlp, then mbox issue fails → explicit lpfc_nlp_put → out_free_mbox → release | release | One lpfc_nlp_get (matched) | One explicit lpfc_nlp_put (matched) | ✅ | Balanced get/put pair; callback reference still held for final put. |
| mbox && !PT2PT, ACC_REGLOGIN: get ndlp, mbox issue succeeds (goto out) → release | release | One lpfc_nlp_get | None (the get is transferred to mbox callback) | ✅ | Callback reference released by final put. |
| else if (mbox && PT2PT && ACC_REGLOGIN) → out → release | release | None extra | None | ✅ | |
| Path after out: where **lpfc_drop_node is called** (SLI_REV4, NPIV_PORT, !SCSI_XPT_REGD, state not in issue list) → then release | release | None extra | **lpfc_drop_node does a PUT that releases the last reference** | ❌ **Excess put** – refcount underflow at final put (line 5612) | **BUG**: lpfc_drop_node drops the last reference, then the unconditional final lpfc_nlp_put(ndlp) causes underflow. |

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
**Reason:** `lpfc_drop_node(vport, ndlp)` at ~line 5602 releases the last reference on ndlp, but the unconditional `lpfc_nlp_put(ndlp)` at release (line 5612) is still executed, causing a kref underflow / excess put warning.
```
