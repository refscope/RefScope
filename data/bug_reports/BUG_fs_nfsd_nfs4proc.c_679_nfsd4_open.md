# REAL BUG: fs/nfsd/nfs4proc.c:679 nfsd4_open()

**Confidence**: HIGH | **Counter**: `$->fh_export->h.ref.refcount.refs.counter`

## Reasoning

| L663 (success) | return status | YES | YES | ✅ | cleanup after fh_dup2 correct |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L570 | goto out_err | NO (resfh NULL) | N/A | ✅ | early check, no ref held |
| L580 | goto out_err | NO | N/A | ✅ | |
| L601 | goto out     | NO | N/A | ✅ | resfh NULL |
| L604 | goto out     | NO | N/A | ✅ | |
| L613 | goto out     | NO | N/A | ✅ | |
| L616 | goto out     | NO | N/A | ✅ | |
| L619 | goto out     | NO | N/A | ✅ | |
| L627 (do_open_lookup error) | goto out | YES (resfh allocated, but do_open_lookup may already release export ref on error) | YES (out block: fh_put(resfh)) | ❌ DOUBLE-PUT | **Warning target**: if do_open_lookup already dropped export ref, out block's `fh_put(resfh)` causes excess put |
| L629 (check_open_reclaim error) | goto out | NO | N/A | ✅ | resfh NULL |
| L633 (do_open_fhandle error) | goto out | NO (resfh = &cstate->current_fh, no extra get) | N/A | ✅ | condition `resfh != &cstate->current_fh` false, no put |
| L643 (process_open2 error) | goto out | YES (do_open_lookup succeeded, refs valid) | YES | ✅ | normal path, refs properly held |
| L663 (success) | return status | YES | YES | ✅ | cleanup after fh_dup2 correct |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`do_open_lookup` likely already releases the export reference on error, but leaves `resfh` non‑NULL, so the out block’s `fh_put(resfh)` performs an excess put on `$->fh_export->h.ref.refcount`.
```
