# REAL BUG: drivers/bluetooth/virtio_bt.c:403 virtbt_probe()

**Confidence**: HIGH | **Counter**: `hdev->dev.kobj.kref.refcount.refs.counter`

## Reasoning

ci_register_dev succeeded) | YES? (calls hci_free_dev) | ❌ | `hci_free_dev` drops the allocation ref but does NOT release the registration hold (from `hci_register_dev`). Correct fix: call `hci_unregister_dev(hdev)` instead. The registration reference is leaked, causing inconsistent refcounting. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L286 | error (-ENODEV) | NO (before any get) | N/A | ✅ | |
| L295 | error (-EINVAL) | NO (before get) | N/A | ✅ | |
| L302 | error (-ENOMEM) | NO (before get) | N/A | ✅ | |
| L311 | error (virtio_find_vqs fail) | NO (before hci_alloc_dev) | N/A | ✅ | |
| L317/L434 (goto failed after hci_alloc_dev fail) | error (-ENOMEM) | NO (hci_alloc_dev failed) | N/A | ✅ | hdev == NULL |
| L403/L434 (goto failed after hci_register_dev fail) | error (-EBUSY) | YES (unconditional get by hci_register_dev, but on failure internal put cancels its hold) | YES (hci_free_dev releases alloc ref) | ✅ | Standard cleanup for failed registration. |
| L426 | success (return 0) | YES (hci_register_dev success, holds ref) | NO (no put needed; ownership transferred to Bluetooth subsystem) | ✅ | |
| L429/open_failed | error (virtbt_open_vdev fail) | YES (hci_register_dev succeeded) | YES? (calls hci_free_dev) | ❌ | `hci_free_dev` drops the allocation ref but does NOT release the registration hold (from `hci_register_dev`). Correct fix: call `hci_unregister_dev(hdev)` instead. The registration reference is leaked, causing inconsistent refcounting. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After successful hci_register_dev, the open_failed error path calls hci_free_dev instead of hci_unregister_dev, leaking the reference held by the Bluetooth subsystem.
```
