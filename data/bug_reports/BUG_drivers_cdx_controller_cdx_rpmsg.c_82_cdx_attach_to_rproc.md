# REAL BUG: drivers/cdx/controller/cdx_rpmsg.c:82 cdx_attach_to_rproc()

**Confidence**: LOW | **Counter**: `rp->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L79→L82 (success) | success (return 0) | YES | NO | ❌ LEAK | rp stored in cdx_mcdi->r5_rproc but not put on this return path; reference held beyond function exit |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L62 | error (-EINVAL) | NO (before get) | N/A | ✅ | of_parse_phandle failed, no rp acquisition |
| L66 (via goto) | goto pdev_err → L82 return | NO (rp NULL, get failed) | N/A | ✅ | rproc_get_by_phandle returned NULL, no reference held |
| L75→L82 | goto pdev_err after rproc_boot failure | YES (L65 succeed) | YES (rproc_put at L75) | ✅ | explicit rproc_put before goto, correct |
| L79→L82 (success) | success (return 0) | YES | NO | ❌ LEAK | rp stored in cdx_mcdi->r5_rproc but not put on this return path; reference held beyond function exit |

VERDICT: REAL_BUG  
CONFIDENCE: LOW  
Success path acquires rp via rproc_get_by_phandle, stores it in cdx_mcdi->r5_rproc, and returns without calling rproc_put, leaving the refcount elevated on that path. No cleanup code (e.g., remove()) is provided to confirm the reference is released elsewhere, so this is flagged as a potential leak.
```
