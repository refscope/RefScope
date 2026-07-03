# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:3729 lpfc_issue_els_rscn()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

| ~L3722 (success) | success (return 0) | YES (initial ref + explicit get) | NO (no put for initial ref) | ❌ LEAK | The explicit get is transferred to the iocb, but the initial reference from *findnode/init* is never released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L3663 (topology check) | error (return 1) | NO (before ndlp) | N/A | ✅ | No ndlp reference obtained |
| ~L3670 (PT2PT ndlp NULL) | error (return 1) | NO (ndlp not obtained) | N/A | ✅ | ndlp remained NULL |
| ~L3681 (nlp_init failure) | error (return 1) | NO | N/A | ✅ | ndlp not obtained |
| ~L3685 (elsiocb alloc fail) | error (return 1) | YES (from findnode/init) | NO | ❌ LEAK | ndlp ref from *findnode_mapped*/*findnode_did*/*nlp_init* is never released |
| ~L3700 (lpfc_nlp_get returns NULL) | error (return 1) | YES (initial ref) | NO | ❌ LEAK | Explicit get failed, but the initial ndlp ref is still held and not put |
| ~L3718 (IOCB_ERROR) | error (return 1) | YES (initial ref + explicit get) | ONE PUT (partial) | ❌ LEAK likely | Single `lpfc_nlp_put(ndlp)` – if two references were held, one remains leaked; if *lpfc_els_free_iocb* drops the iocb’s reference the initial ref might be balanced here, but still inconsistent with success path |
| ~L3722 (success) | success (return 0) | YES (initial ref + explicit get) | NO (no put for initial ref) | ❌ LEAK | The explicit get is transferred to the iocb, but the initial reference from *findnode/init* is never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The function acquires a reference to `ndlp` via `lpfc_findnode_mapped()`, `lpfc_findnode_did()`, or `lpfc_nlp_init()` but never releases it on the success path (`return 0`) nor on the early error paths (elsiocb alloc failure, `lpfc_nlp_get` NULL); only the `IOCB_ERROR` path does a single `lpfc_nlp_put()` which is not enough to balance all held references, resulting in a refcount leak and the inconsistent refcounting flagged by smatch.
```
