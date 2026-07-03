# REAL BUG: drivers/gpu/drm/msm/adreno/a6xx_gmu.c:2443 a6xx_gmu_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| (success return 0) | success | YES | NO (ownership transfer) | ✅ | Reference held via `gmu->dev`, caller responsible |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|---|---|---|---|---|---|
| (early, no pdev) | error return -ENODEV | NO (pdev NULL) | N/A | ✅ | No get, no put |
| (after of_dma_configure failure) | error return ret | YES | NO | ❌ LEAK | Early return skips `err_put_device` |
| (goto err_put_device) | error via label | YES | YES | ✅ | |
| (goto err_memory) | error via label | YES | YES (fallthrough) | ✅ | `err_memory` → `err_put_device` |
| (goto err_mmio) | error via label | YES | YES (fallthrough) | ✅ | `err_mmio` → … → `err_put_device` |
| (goto detach_cxpd) | error via label | YES | YES (fallthrough) | ✅ | `detach_cxpd` → `err_mmio` → … → `put_device` |
| (goto detach_gxpd) | error via label | YES | YES (fallthrough) | ✅ | `detach_gxpd` → `detach_cxpd` → … → `put_device` |
| (success return 0) | success | YES | NO (ownership transfer) | ✅ | Reference held via `gmu->dev`, caller responsible |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**
`of_dma_configure` failure returns directly without `put_device`, leaking the reference acquired by `of_find_device_by_node`.
```
