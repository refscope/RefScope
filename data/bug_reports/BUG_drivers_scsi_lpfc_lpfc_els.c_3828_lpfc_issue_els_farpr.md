# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:3828 lpfc_issue_els_farpr()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

| 3828 | success (return 0) | YES (successful get) | NO (put deferred to iocb completion) | ✅ | Reference held in elsiocb; will be released later by `lpfc_cmpl_els_cmd`/iocb free. |

## Full Response

```
| Line | Return Type | GET Done? (lpfc_nlp_get) | PUT Done? (explicit lpfc_nlp_put) | Balance? | Notes |
|------|-------------|----------------------------|-----------------------------------|-----------|-------|
| 3770 | error (ndlp NULL after init fail) | NO (get not yet called) | N/A | ✅ | No reference acquired. |
| 3778 | error (elsiocb alloc fail) | NO (get not yet called) | N/A | ✅ | No reference from this function’s get. However, if ndlp reference was obtained via find/init, missing put would be a leak – but that is not captured by this table’s tracked get. |
| 3813 | error (lpfc_nlp_get returns NULL) | FAIL (no ref taken) | N/A | ✅ | Conditional get failed; object may be dead, put would be UAF. |
| 3821 | error (IOCB_ERROR) | YES (successful get) | YES (explicit lpfc_nlp_put) | ❌ **BUG** | **Double put:** `lpfc_els_free_iocb` will also release the get reference stored in `elsiocb->ndlp`, so the explicit put here over-releases the reference, risking premature freeing. |
| 3828 | success (return 0) | YES (successful get) | NO (put deferred to iocb completion) | ✅ | Reference held in elsiocb; will be released later by `lpfc_cmpl_els_cmd`/iocb free. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

On the IOCB_ERROR path at line 3821, `lpfc_nlp_get` took a reference, but the function performs both an explicit `lpfc_nlp_put(ndlp)` and frees the iocb (which later releases the same `elsiocb->ndlp` reference), leading to a double‑put/refcount underflow. The other error paths do not suffer from this extra put, making the refcounting inconsistent and likely triggering a use‑after‑free or premature node release.
```
