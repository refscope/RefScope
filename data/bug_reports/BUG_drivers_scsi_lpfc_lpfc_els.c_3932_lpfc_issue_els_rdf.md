# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:3932 lpfc_issue_els_rdf()

**Confidence**: HIGH | **Counter**: `ndlp->kref.refcount.refs.counter`

## Reasoning

| 3921 return 0 | success | YES (initial ref present) | YES (get success) | NO | ❌ (initial ref leak) | elsiocb->ndlp ref will be released in completion; initial ref from findnode/init never released |

## Full Response

```
| Line | Return Type | Initial Ref? (from findnode/init) | Extra GET? (lpfc_nlp_get) | PUT on ndlp? | Balanced? | Notes |
|------|-------------|-----------------------------------|---------------------------|----------------|-----------|-------|
| 3858 | return -EACCES | NO (before ndlp) | N/A | N/A | ✅ | no ndlp |
| 3863 | return -ENODEV | NO (init failed) | N/A | N/A | ✅ | no ndlp |
| 3883 goto out_node_created | error (elsiocb alloc fail) | YES (initial ref present) | NO | YES if node_created, else NO | ❌ if !node_created: leak of initial findnode ref | found node’s ref never released |
| 3907 goto out_free_iocb → out_node_created | error (lpfc_nlp_get fail) | YES (initial ref present) | NO (get failed) | YES if node_created, else NO | ❌ if !node_created: leak | same as above |
| 3917 goto out_iocb_error → out_free_iocb → out_node_created | error (iocb submit fail) | YES (initial ref present) | YES (get success, elsiocb->ndlp set) | YES (unconditional put at out_iocb_error) + YES again if node_created (double put) | ❌ (double put when node_created; extra ref from get leaked and wrong pointer put) | puts original ndlp, not elsiocb->ndlp; elsiocb->ndlp ref never released |
| 3921 return 0 | success | YES (initial ref present) | YES (get success) | NO | ❌ (initial ref leak) | elsiocb->ndlp ref will be released in completion; initial ref from findnode/init never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the iocb error path (line 3917) the code puts the wrong pointer `ndlp` instead of `elsiocb->ndlp`, leading to a double put if the node was created earlier and a leak of the reference acquired by `lpfc_nlp_get()`.
```
