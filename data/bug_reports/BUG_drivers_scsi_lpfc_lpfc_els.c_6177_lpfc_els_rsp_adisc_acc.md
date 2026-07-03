# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:6177 lpfc_els_rsp_adisc_acc()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

back (`lpfc_cmpl_els_rsp`) is the normal owner for success, it is standard that `lpfc_els_free_iocb()` itself releases the ndlp reference when the IOCB is aborted before submission. The additional manual `lpfc_nlp_put()` then creates a double decrement, exactly matching the “inconsistent” warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L6116 | error (return 1) | NO (before get) | N/A | ✅ | elsiocb allocation failed, ndlp untouched. |
| L6172 | error (return 1) | NO (conditional get failed, elsiocb->ndlp == NULL) | N/A | ✅ | No reference taken; lpfc_els_free_iocb() cleans up IOCB only. |
| L6177 | error (IOCB_ERROR, return 1) | YES (lpfc_nlp_get() succeeded) | YES (explicit lpfc_nlp_put(ndlp)) + implicit from lpfc_els_free_iocb()? | ❌ **DOUBLE PUT** if lpfc_els_free_iocb() also releases ndlp | GET succeeded, then free IOCB (probable ndlp release) plus explicit put → inconsistent refcount. |
| L6181 | success (return 0) | YES | NO in this function | ✅ (ownership transferred) | ndlp reference held by iocb->ndlp, released via lpfc_cmpl_els_rsp callback. |

[NEED_SOURCE] lpfc_els_free_iocb

**Analysis:**  
The warning line `6177` and the `inconsistent refcounting` on `ndlp->kref` point directly at the error-path cleanup for `IOCB_ERROR` after a successful `lpfc_nlp_get()`. In this path the code calls both `lpfc_els_free_iocb()` and an explicit `lpfc_nlp_put(ndlp)`. Since `elsiocb->ndlp` holds the acquired reference and the completion callback (`lpfc_cmpl_els_rsp`) is the normal owner for success, it is standard that `lpfc_els_free_iocb()` itself releases the ndlp reference when the IOCB is aborted before submission. The additional manual `lpfc_nlp_put()` then creates a double decrement, exactly matching the “inconsistent” warning.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
