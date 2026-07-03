# REAL BUG: drivers/net/wireless/ath/ath10k/snoc.c:1690 ath10k_fw_init()

**Confidence**: HIGH | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

**Note:** The `of_node_put(node)` at line 1690 corresponds exactly to the warning line. All paths after `pdev->dev.of_node = node` incorrectly release the reference, causing a double put when the device is eventually unregistered.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1627: `if (!node) return 0` | early return (node NULL) | NO (node=NULL) | N/A | ✅ | No ref acquired. |
| ~L1637: `IS_ERR(pdev)` → `return PTR_ERR(pdev)` | error (device not registered) | YES (node != NULL) | YES (`of_node_put(node)` before return) | ✅ | Proper put before any ownership transfer; device not created. |
| ~L1642: `goto err_unregister` (of_dma_configure fail) | error (device registered) | YES | YES (via `err_unregister`: `platform_device_unregister(pdev)` + `of_node_put(node)`) | ❌ DOUBLE PUT | `pdev->dev.of_node = node` already transferred ownership to device core. The `platform_device_unregister` will later release the reference via `device_release` → `of_node_put`. The extra `of_node_put` here is a double put. |
| ~L1650: `goto err_unregister` (iommu_domain_alloc fail) | error (device registered) | YES | YES (same as above) | ❌ DOUBLE PUT | Same as above. |
| ~L1656: `goto err_iommu_free` → falls through to `err_unregister` | error | YES | YES (same as above) | ❌ DOUBLE PUT | Same as above. |
| ~L1662: `goto err_iommu_detach` → falls through to `err_unregister` | error | YES | YES (same as above) | ❌ DOUBLE PUT | Same as above. |
| ~L1690: `return 0` (success) | success | YES | YES (`of_node_put(node)` at L1690) | ❌ DOUBLE PUT | After setting `pdev->dev.of_node = node`, the reference is owned by the device. The device core will release it on unregister. This manual put will be followed by a device‑core put → double put. |

**Note:** The `of_node_put(node)` at line 1690 corresponds exactly to the warning line. All paths after `pdev->dev.of_node = node` incorrectly release the reference, causing a double put when the device is eventually unregistered.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pdev->dev.of_node = node` transfers the ref to the device core, making any subsequent `of_node_put(node)` in this function (success or error‑unregister) a double put.
```
