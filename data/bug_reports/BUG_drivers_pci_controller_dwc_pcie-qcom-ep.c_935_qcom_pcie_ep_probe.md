# REAL BUG: drivers/pci/controller/dwc/pcie-qcom-ep.c:935 qcom_pcie_ep_probe()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L926 | success return 0 | YES | YES | ✅ | put_sync at L917 |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L895 | error return (ret) | YES (unconditional get at L891) | NO (no put call) | ❌ LEAK | Early return after devm_pm_runtime_enable fails |
| L899 | error return (ret) | YES | NO | ❌ LEAK | After get_resources failure |
| L904 | error return (ret) | YES | NO | ❌ LEAK | After dw_pcie_ep_init failure |
| L909 (goto err_ep_deinit → L935) | error return (ret) | YES | NO | ❌ LEAK | err_ep_deinit only calls dw_pcie_ep_deinit, no pm_runtime_put |
| L914 (goto err_disable_irqs → L935) | error return (ret) | YES | NO | ❌ LEAK | err_disable_irqs falls through to err_ep_deinit, no put |
| L920 (goto err_disable_irqs → L935) | error return (ret) | YES | YES (put_sync at L917) | ✅ | put_sync already executed before goto |
| L926 | success return 0 | YES | YES | ✅ | put_sync at L917 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_noresume` unconditionally increments usage_count; multiple error paths (L895, L899, L904, L909→L935, L914→L935) return without calling `pm_runtime_put_sync`, leaking the reference.
```
