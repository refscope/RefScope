# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:9080 lpfc_issue_els_rrq()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

| L5: ret == IOCB_BUSY (or any non-error) → return 0 | success-like return | YES | NO | ❌ LEAK | IOCB not submitted, completion never fires, ndlp reference left in leaked elsiocb. Refcount never decremented. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1: if(!ndlp) return 1 | error return | NO (ndlp is NULL) | N/A | ✅ | No reference |
| L2: if(!elsiocb) return 1 | error return | NO (before get) | N/A | ✅ | |
| L3: if(!elsiocb->ndlp) goto io_err | error (lpfc_nlp_get failed) | NO (lpfc_nlp_get returned NULL) | N/A | ✅ | io_err → lpfc_els_free_iocb only, no put |
| L4: ret == IOCB_ERROR → lpfc_nlp_put(ndlp); goto io_err | error return | YES (lpfc_nlp_get succeeded) | YES (explicit put before goto) | ✅ | |
| L5: ret == 0 (success) → return 0 | success | YES | NO (transferred to completion) | ⚠️ Potential OK (completion puts) | No put in function, but reference held by elsiocb->ndlp until completion; standard ownership transfer pattern. |
| L5: ret == IOCB_BUSY (or any non-error) → return 0 | success-like return | YES | NO | ❌ LEAK | IOCB not submitted, completion never fires, ndlp reference left in leaked elsiocb. Refcount never decremented. |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

When `lpfc_sli_issue_iocb` returns `IOCB_BUSY` (or any value other than `IOCB_ERROR` or 0), the code at L9080 takes the success return path without calling `lpfc_nlp_put(ndlp)`. Since the IOCB was not queued, the completion callback (`lpfc_cmpl_els_rrq`) will never run, and the reference acquired via `lpfc_nlp_get` is never released, causing a refcount leak on `ndlp`.
```
