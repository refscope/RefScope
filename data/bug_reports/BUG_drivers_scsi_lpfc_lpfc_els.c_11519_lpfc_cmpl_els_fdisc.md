# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:11519 lpfc_cmpl_els_fdisc()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L11508 (goto out) | fall-through to out | YES | YES (out) | ✅ | final success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L11421 (goto out) | fall-through to out | YES (caller holds ref) | YES (out put L11518) | ✅ | no prior put |
| L11426 (goto out) | fall-through to out | YES | YES (out) | ✅ | no prior put |
| L11434 (lpfc_nlp_put) + L11436 (goto fdisc_failed → out) | fall-through to out | YES | YES (L11434) + YES (out L11518) | ❌ EXCESS PUT | If NLP_DROPPED not set → double put. If set → single put (not flagged) |
| L11451 (goto out) | fall-through to out | YES | YES (out) | ✅ | prsp NULL early exit |
| L11453 (goto out) | fall-through to out | YES | YES (out) | ✅ | not acc response early exit |
| L11494 (goto out) | fall-through to out | YES | YES (out) | ✅ | after lpfc_register_new_vport/set_state |
| L11508 (goto out) | fall-through to out | YES | YES (out) | ✅ | final success path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the ulp_status error path, when NLP_DROPPED is not set, `lpfc_nlp_put(ndlp)` at L11434 drops the reference, then the code falls through `fdisc_failed` to `out:` where `lpfc_nlp_put(ndlp)` at L11518 is called again, causing an excess kref_put that triggers the warning.
```
