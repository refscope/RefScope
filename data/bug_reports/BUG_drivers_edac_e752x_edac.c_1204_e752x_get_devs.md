# REAL BUG: drivers/edac/e752x_edac.c:1204 e752x_get_devs()

**Confidence**: HIGH | **Counter**: `pvt->dev_d0f1->dev.kobj.kref.refcount.refs.counter`

## Reasoning

o fail, return 1) | YES (dev_d0f1 non‑NULL, same get as success path) | YES (pci_dev_put at L1203) | ❌ LEAK on pci_scan_single_device path | pci_get_device success: one get, one put → ok. pci_scan_single_device success: implicit get from scan + explicit pci_dev_get = two gets, one put → ref leak |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1190 | error (return 1) | NO (dev_d0f1 is NULL, both get attempts failed) | N/A | ✅ | No reference held |
| L1200 | success (return 0) | YES (dev_d0f1: ref from pci_get_device OR pci_scan_single_device + pci_dev_get; dev_d0f0: ref from pci_get_device) | NO (ownership transferred to caller) | ⚠️ (leak in caller) | caller will put both once, but if pci_scan_single_device path was taken, the extra pci_dev_get gives an unaccounted reference, causing a leak later |
| L1198→L1204 | error (goto fail, return 1) | YES (dev_d0f1 non‑NULL, same get as success path) | YES (pci_dev_put at L1203) | ❌ LEAK on pci_scan_single_device path | pci_get_device success: one get, one put → ok. pci_scan_single_device success: implicit get from scan + explicit pci_dev_get = two gets, one put → ref leak |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pci_scan_single_device` returns a device with a reference that must be put; the explicit `pci_dev_get` on top of that creates an extra reference. On the goto-fail error path only one `pci_dev_put` is executed, leaking the extra ref (and the success path will leak later).
```
