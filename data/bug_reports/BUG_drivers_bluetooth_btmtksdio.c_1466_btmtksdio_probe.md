# REAL BUG: drivers/bluetooth/btmtksdio.c:1466 btmtksdio_probe()

**Confidence**: HIGH | **Counter**: `$->dev.kobj.kref.refcount.refs.counter`

## Reasoning

[NEED_SOURCE] **hci_register_dev** — to confirm whether the function drops its own kref on error, which would make the ~L1415 path balanced or a leak.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1371 | error (ENOMEM) | NO (before hci_alloc_dev) | N/A | ✅ | devm_kzalloc failure |
| ~L1378 | error (ENODEV) | NO | N/A | ✅ | bdev->data NULL |
| ~L1389 | error (ENOMEM) | NO (hci_alloc_dev failed) | N/A | ✅ | NULL hdev |
| ~L1415 | error (hci_register_dev failed) | YES (hci_register_dev unconditional hold) | PARTIAL (hci_free_dev drops initial ref; hci_register_dev may or may not drop its hold on error) | ⚠️ UNCLEAR | hci_free_dev is called, but if hci_register_dev held an extra ref and didn’t drop on error, leak persists. Needs source for hci_register_dev error path. |
| **L1466** | **error / success** | **YES (hci_register_dev succeeded)** | **NO** | **❌ LEAK** | **After hci_register_dev success, later steps set err (devm_device_init_wakeup or gpiod_get_optional error) and the probe returns error without hci_unregister_dev/hci_free_dev. The HCI device’s kref is leaked and the device is left registered.** |

## Requested Source
[NEED_SOURCE] **hci_register_dev** — to confirm whether the function drops its own kref on error, which would make the ~L1415 path balanced or a leak.

---

## VERDICT: REAL_BUG

## CONFIDENCE: HIGH

**Reason**: After `hci_register_dev` succeeds, probe may encounter errors (e.g., from `devm_gpiod_get_optional`) and return non-zero at line 1466 without calling `hci_unregister_dev` or `hci_free_dev`. This leaks the HCI device’s kref and leaves the device registered. Probe error paths after registration must release the HCI device; the lack of such release is a clear refcount imbalance.
```
