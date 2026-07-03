# REAL BUG: drivers/scsi/libsas/sas_expander.c:864 sas_ex_discover_end_dev()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L860 (return child)  | success | YES | NO (ownership transferred to parent_ex->children) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L812 (return NULL)   | early sata host/ps check | NO (before child allocation) | N/A  | ✅ | |
| L816 (return NULL)   | alloc failed | NO (get failed, child is NULL) | N/A  | ✅ | |
| L832 (goto out_err)  | port alloc fail | YES (child ref=1 from alloc) | YES (sas_put_device at out_err) | ✅ | single put, correct |
| L835 (goto out_err)  | sas_port_add fail | YES | YES | ✅ | single put, correct |
| L857 (goto out_free) | add_dev failed (res != 0) | YES | YES (sas_put_device via out_err) | **❓** | if callee (sas_ata_add_dev / sas_ex_add_dev) already dropped the child reference on error, this is an excess put; warning points here |
| L860 (return child)  | success | YES | NO (ownership transferred to parent_ex->children) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The warning at L864 (excess put on child’s kref) indicates that when `sas_ata_add_dev` or `sas_ex_add_dev` returns an error, the child’s reference count has already been decremented (likely freed), making the caller’s `sas_put_device(child)` a double-put. Without the callee source this cannot be fully verified, but the static analysis tracked the double put across functions.
```
