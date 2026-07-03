# REAL BUG: drivers/usb/typec/ucsi/ucsi_ccg.c:1506 ucsi_ccg_probe()

**Confidence**: HIGH | **Counter**: `uc->dev->power.usage_count.counter`

## Reasoning

| L1506 (success, return 0) | return 0 | NO | YES (pm_runtime_idle) | ❌ EXCESS PUT | pm_runtime_idle decrements usage_count but no prior pm_runtime_get |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1434 (approx) | error (-ENOMEM) | NO | N/A | ✅ | before any pm get |
| L1457 (ucsi_ccg_init fail) | error (status) | NO | N/A | ✅ | no pm get |
| L1462 (get_fw_info fail) | error (status) | NO | N/A | ✅ | no pm get |
| L1471 (ucsi_create fail) | error (PTR_ERR) | NO | N/A | ✅ | no pm get |
| L1477 (goto out_ucsi_destroy) | error (status) | NO | NO | ✅ | no pm put needed |
| L1480 (goto out_free_irq) | error (status) | NO | NO | ✅ | no pm put needed |
| L1506 (success, return 0) | return 0 | NO | YES (pm_runtime_idle) | ❌ EXCESS PUT | pm_runtime_idle decrements usage_count but no prior pm_runtime_get |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_idle()` at the end of the probe is called without any prior `pm_runtime_get*` (neither in the function body nor via an explicit get call). The PM usage count starts at 0, so `pm_runtime_idle` underflows it, exactly matching the “excess put” warning.
```
