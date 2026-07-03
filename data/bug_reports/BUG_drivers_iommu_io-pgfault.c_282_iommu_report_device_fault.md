# REAL BUG: drivers/iommu/io-pgfault.c:282 iommu_report_device_fault()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

| ~240 (return 0) | success | YES | Transferred to group | ✅ | Group holds reference, will be released later by iopf_free_group |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~220 (goto err_bad_iopf) | error | NO (before get) | N/A | ✅ | iopf_get_dev_fault_param not called yet |
| ~224 (goto err_bad_iopf) | error (iopf_param NULL) | NO (get failed) | N/A | ✅ | Conditional get returned NULL, no ref held |
| ~230 (return ret) | partial fault return | YES | YES | ✅ | Explicit iopf_put_dev_fault_param before return |
| ~235 (goto err_abort, group == &abort_group) | error return 0 via err_abort | YES | NO | ❌ LEAK | iopf_group_alloc failed; ownership not transferred, caller still holds ref from iopf_get_dev_fault_param |
| ~238 (goto err_abort, handler fails) | error return 0 via err_abort | YES | Transferred to group | ✅ | Group holds reference, released by iopf_free_group in err_abort per comment |
| ~240 (return 0) | success | YES | Transferred to group | ✅ | Group holds reference, will be released later by iopf_free_group |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `iopf_group_alloc()` fails (group == &abort_group) at ~L255, the function jumps to `err_abort` which never calls `iopf_put_dev_fault_param()`. The caller’s reference acquired by `iopf_get_dev_fault_param()` is leaked because ownership was not transferred to a valid group and no put is performed.
```
