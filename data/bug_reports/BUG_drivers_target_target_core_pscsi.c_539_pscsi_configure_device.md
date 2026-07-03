# REAL BUG: drivers/target/target_core_pscsi.c:539 pscsi_configure_device()

**Confidence**: HIGH | **Counter**: `$->shost_gendev.kobj.kref.refcount.refs.counter`

## Reasoning

| 510–514 | error (-ENODEV) | YES | ❌ (same conditional put as above) | ❌ LEAK | loop finished, no device found; put only if PHV_VIRTUAL_HOST_ID |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 436 | error (-EINVAL) | NO (before get) | N/A | ✅ | early param checks |
| 442 | error (-ENODEV) | NO (before get) | N/A | ✅ | !sh & PHV_LLD_SCSI_HOST_NO |
| 449 | error (-EINVAL) | NO (before get) | N/A | ✅ | !sh & !DF_USING_UDEV_PATH |
| 456 | error (-EEXIST) | NO (before get) | N/A | ✅ | !sh, no PDF_HAS_VIRT_HOST_ID, dev_count |
| 459 | error (-ENODEV) | NO (before get) | N/A | ✅ | pscsi_pmode_enable_hba fails |
| 466 | success (continue) | NO | N/A | ✅ | legacy mode: sh = phv->phv_lld_host, no get |
| 468 | error (-EINVAL) | NO (scsi_host_lookup failed) | N/A | ✅ | lookup returned NULL, no ref held |
| 478 | error (-EEXIST) | NO (sh already set, no get) | N/A | ✅ | sh exists, PHV_VIRTUAL_HOST_ID check |
| 497–502 | error (ret) | YES (lookup succeeded) | ❌ (only if phv_mode==PHV_VIRTUAL_HOST_ID, else none) | ❌ LEAK | error after pscsi_create_type_*, put guarded by mode, other modes leak |
| 504 | success (0) | YES | no (ownership transfer) | ✅ | SCSI device registered, host ref retained for device lifetime |
| 510–514 | error (-ENODEV) | YES | ❌ (same conditional put as above) | ❌ LEAK | loop finished, no device found; put only if PHV_VIRTUAL_HOST_ID |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`scsi_host_lookup()` acquires a reference (via `scsi_host_get`) unconditionally when its return is non‑NULL. On all error paths after that point (device registration failure and “device not found”), the matching `scsi_host_put()` is guarded by `if (phv->phv_mode == PHV_VIRTUAL_HOST_ID)`, but the lookup was performed solely based on `PDF_HAS_VIRT_HOST_ID` without checking `phv_mode`. If another mode is active, the reference is never released, causing a refcount leak.
```
