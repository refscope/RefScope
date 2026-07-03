# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:6681 lpfc_els_disc_adisc()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

ence) | YES (unconditional `lpfc_nlp_put` inside callee) | ❌ EXCESS PUT | `lpfc_issue_els_adisc` unconditionally calls `lpfc_nlp_put`. The caller iterates the list without acquiring a reference, so the first `put` can underflow the refcount when the ndlp does not already have an extra reference. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L6675 (call `lpfc_issue_els_adisc`) → L6680 | return `sentadisc` | NO (caller did not grab reference) | YES (unconditional `lpfc_nlp_put` inside callee) | ❌ EXCESS PUT | `lpfc_issue_els_adisc` unconditionally calls `lpfc_nlp_put`. The caller iterates the list without acquiring a reference, so the first `put` can underflow the refcount when the ndlp does not already have an extra reference. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`lpfc_issue_els_adisc` unconditionally puts ndlp’s kref, but `lpfc_els_disc_adisc` does not `lpfc_nlp_get()` before the call, leading to an excess put when the refcount is already zero or minimal.
```
