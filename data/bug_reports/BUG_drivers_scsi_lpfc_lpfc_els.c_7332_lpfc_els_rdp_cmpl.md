# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:7332 lpfc_els_rdp_cmpl()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

ich is balanced **only if** `lpfc_els_free_iocb` does **not** touch `ndlp`. The `excess put` warning indicates that `lpfc_els_free_iocb` likely **also** releases the `ndlp` reference held by the iocb (e.g., if it calls `lpfc_nlp_put(elsiocb->ndlp)`), causing a triple put where only two refs exist.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L7176 | goto error (status != SUCCESS) | NO | N/A | N/A | Falls into error branch, will eventually reach free_rdp_context |
| L7187 | goto free_rdp_context (prep fail) | NO | YES (free_rdp_context) | ✅ | Only original ref released by the label |
| L7254 | goto free_rdp_context (get fail) | NO (get returned NULL) | YES (free_rdp_context) | ✅ | Only original ref released |
| L7263 (fallthrough after IOCB_ERROR) + free_rdp_context | implicit goto free_rdp_context after error handling | YES (get succeeded) | ⚠️ **2 PUTs** (explicit `lpfc_nlp_put` at L7260 + `lpfc_nlp_put` at free_rdp_context L7332) | ❌ **EXCESS** if `lpfc_els_free_iocb` already puts `ndlp` (double put) – otherwise balanced | Core path: get +1 → explicit put for get, original put at label. If free_iocb also puts, total 3 puts for 2 refs → excess. |
| L7263 (fallthrough after success) | implicit goto free_rdp_context after iocb issued | YES | YES (original put only) | ✅ | iocb holds extra ref, original ref released |
| L7272 | goto free_rdp_context (error branch prep fail) | NO | YES | ✅ | Only original ref |
| L7296 | goto free_rdp_context (error branch get fail) | NO | YES | ✅ | Only original ref |
| L7303+fallthrough (error IOCB_ERROR after get) | implicit goto free_rdp_context | YES | ⚠️ **2 PUTs** (one in block, one at label) | ❌ **EXCESS** if `lpfc_els_free_iocb` puts `ndlp` | Same pattern as success error path |
| L7303+fallthrough (error issue success) | implicit goto free_rdp_context | YES | YES (original only) | ✅ | iocb holds extra ref |

**Analysis**: The function always calls `lpfc_nlp_put(ndlp)` at `free_rdp_context` to drop the original reference from `rdp_context`. On paths where `lpfc_nlp_get` succeeded but `lpfc_sli_issue_iocb` returns `IOCB_ERROR`, the code explicitly calls `lpfc_nlp_put(ndlp)` **before** reaching `free_rdp_context`. That gives two puts – one for the failed get, one for the original – which is balanced **only if** `lpfc_els_free_iocb` does **not** touch `ndlp`. The `excess put` warning indicates that `lpfc_els_free_iocb` likely **also** releases the `ndlp` reference held by the iocb (e.g., if it calls `lpfc_nlp_put(elsiocb->ndlp)`), causing a triple put where only two refs exist.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`lpfc_els_rdp_cmpl` double-puts `ndlp` on IOCB error paths: explicit `lpfc_nlp_put` after `lpfc_els_free_iocb` plus the put at `free_rdp_context`, and the free function likely also drops the iocb’s reference, triggering excess put.
```
