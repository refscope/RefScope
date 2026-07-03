# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:8837 lpfc_els_rsp_rls_acc()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

ive**: If `lpfc_els_free_iocb` did **not** put the ndlp, there would be exactly one get and one put, which would be balanced and could not cause an excess put. The presence of the excess-put warning at the function exit (L8837) thus strongly implies `lpfc_els_free_iocb` does release the reference.

## Full Response

```
| Line | Return Type | GET Done? (lpfc_nlp_get) | PUT Done? (lpfc_nlp_put) | Balanced? | Notes |
|------|-------------|--------------------------|--------------------------|-----------|-------|
| L8777 | error (mbxStatus) | NO (get not called) | NO (no put) | ❌ LEAK | pmb's ndlp reference leaked — but warning is excess put, not leak |
| L8790 | error (!elsiocb) | NO (get not called) | YES (put at 8786 releases pmb reference) | ✅ | No later get; balance correct |
| L8829 | error (get failed) | NO (get returned NULL, no ref held) | NO (no put) | ✅ | get failed → no ref → no put needed |
| L8837 (via error block) | error (rc == IOCB_ERROR) | YES (get succeeded at L8826) | YES (explicit put at L8835) AND likely put inside lpfc_els_free_iocb → double put | ❌ EXCESS PUT | Double put for one get; warning is excess put at this return |
| L8837 (success, rc != IOCB_ERROR) | success | YES (get succeeded) | NO (no explicit put; iocb will put in completion) | ✅ | Deferred release via iocb callback |

## Analysis

1. **Initial ndlp reference**: `ndlp = pmb->ctx_ndlp` transfers a reference from the mailbox; the comment at L8785 says “Decrement the ndlp reference count from previous mbox command”, and `lpfc_nlp_put(ndlp)` at L8786 releases it. That is balanced for paths that reach L8786 (L8790). Early return at L8777 leaks this reference, but the warning is about *excess* put, not leak.

2. **Later get for iocb**: At L8826, `lpfc_nlp_get(ndlp)` (conditional get) succeeds → refcount incremented.

3. **Error path double-put**: On the `IOCB_ERROR` branch:
   - `lpfc_els_free_iocb()` is called on the iocb, which **very likely** calls `lpfc_nlp_put()` on the ndlp pointer stored in `elsiocb->ndlp`. This is a standard driver pattern: freeing an iocb releases all owned references.
   - Then the code calls `lpfc_nlp_put(ndlp)` explicitly at L8835.
   Result: **two puts for one active get**, causing the refcount to drop one too many → “refcount excess put”.

4. **Why not a false positive**: If `lpfc_els_free_iocb` did **not** put the ndlp, there would be exactly one get and one put, which would be balanced and could not cause an excess put. The presence of the excess-put warning at the function exit (L8837) thus strongly implies `lpfc_els_free_iocb` does release the reference.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`lpfc_els_free_iocb` releases the ndlp reference stored in `elsiocb->ndlp`; the explicit `lpfc_nlp_put(ndlp)` at line 8835 causes a double-put on the `IOCB_ERROR` path.
```
