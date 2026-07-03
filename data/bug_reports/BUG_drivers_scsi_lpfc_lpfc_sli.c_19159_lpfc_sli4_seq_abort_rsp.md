# REAL BUG: drivers/scsi/lpfc/lpfc_sli.c:19159 lpfc_sli4_seq_abort_rsp()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

n (success path, callback releases get) | YES (get succeeded, callback owns ref) | NO (get ref will be released by callback) + conditional final put at L19159 | ❌ excess put if ndlp from findnode and condition true | Calldown put of initial ref is extra when ndlp was found (no initial ref held). |

## Full Response

```
```
| Line | Return Type | GET Done? (lpfc_nlp_get) | PUT Done? (lpfc_nlp_put for get ref) | Balanced? | Notes |
|------|-------------|---------------------------|--------------------------------------|-----------|-------|
| L19025 | early return (link down) | NO | N/A | ✅ | Before any ndlp operation |
| L19038 | early return (ndlp alloc fail) | NO | N/A | ✅ | ndlp is NULL |
| L19047 | early return (ctiocb alloc fail) | NO | NO (ndlp possibly initialized but no put) | ⚠️ Potential leak, but not excess put |
| L19057 | early return (lpfc_nlp_get NULL) | NO (get failed) | N/A | ✅ | No get ref held; possible leak of initial ref if ndlp was allocated |
| L19153 (IOCB_ERROR) → L19159 final block | implicit return (error path) | YES (get succeeded) | YES (lpfc_nlp_put in error block for get ref) + conditional final put at L19159 | ❌ excess put if ndlp from findnode and condition true | Final put releases a reference not held by caller (initial ref assumed from init, but findnode gives no ref). |
| Normal exit (success) → L19159 final block | implicit return (success path, callback releases get) | YES (get succeeded, callback owns ref) | NO (get ref will be released by callback) + conditional final put at L19159 | ❌ excess put if ndlp from findnode and condition true | Calldown put of initial ref is extra when ndlp was found (no initial ref held). |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the final block, lpfc_nlp_put(ndlp) unconditionally releases an “initial reference” that only exists when ndlp was freshly created by lpfc_nlp_init; when ndlp is obtained via lpfc_findnode_did (no reference taken) and its state is NLP_STE_UNUSED_NODE, this call decrements a refcount that was never incremented, causing the “refcount excess put” warning.
```
```
