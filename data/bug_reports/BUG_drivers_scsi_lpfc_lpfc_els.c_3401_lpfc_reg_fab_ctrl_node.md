# REAL BUG: drivers/scsi/lpfc/lpfc_els.c:3401 lpfc_reg_fab_ctrl_node()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L48  | return 0      | YES                                   | NO                                  | ❌ LEAK    | success path, ns_ndlp never released |

## Full Response

```
| Line | Return Type | GET Done? (ns_ndlp from lpfc_findnode_did) | PUT Done? (lpfc_nlp_put on ns_ndlp) | Balanced? | Notes |
|------|-------------|---------------------------------------------|-------------------------------------|-----------|-------|
| L9   | return 0    | NO (before find)                            | N/A                                 | ✅         | `test_bit` early exit |
| L13  | return -ENODEV | NO (find returned NULL)                   | N/A                                 | ✅         | `lpfc_findnode_did` failed, no ref held |
| L17  | return -ENODEV | YES (ns_ndlp non‑NULL)                  | NO                                  | ❌ LEAK    | state mismatch, leaked reference |
| L22  | return -ENOMEM | YES (ns_ndlp non‑NULL)                  | NO                                  | ❌ LEAK    | `mempool_alloc` failed, leaked reference |
| L27  | goto out      | YES                                   | NO                                  | ❌ LEAK    | `lpfc_reg_rpi` error, `out:` does not release ns_ndlp |
| L35  | goto out      | YES                                   | NO                                  | ❌ LEAK    | `lpfc_nlp_get(fc_ndlp)` failed, `out:` does not release ns_ndlp |
| L43  | goto out      | YES                                   | NO                                  | ❌ LEAK    | `MBX_NOT_FINISHED`, puts fc_ndlp but not ns_ndlp |
| L48  | return 0      | YES                                   | NO                                  | ❌ LEAK    | success path, ns_ndlp never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`lpfc_findnode_did` returns a referenced `ns_ndlp` pointer; the function never calls `lpfc_nlp_put(ns_ndlp)` on any exit path, causing a reference leak on the NameServer node.
```
