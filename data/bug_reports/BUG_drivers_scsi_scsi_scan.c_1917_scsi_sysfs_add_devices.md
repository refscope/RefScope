# REAL BUG: drivers/scsi/scsi_scan.c:1917 scsi_sysfs_add_devices()

**Confidence**: HIGH | **Counter**: `$->sdev_gendev.kobj.kref.refcount.refs.counter`

## Reasoning

- Even if `__scsi_remove_device` removes the device from the host’s list, the iterator’s internal pointer to the previous device remains and will be put regardless.

## Full Response

```
## Path Table

| Line   | Return Type           | GET Done? | PUT Done? | Balanced? | Notes |
|--------|-----------------------|-----------|-----------|-----------|-------|
| L1919  | continue (SDEV_DEL)   | YES (iterator holds ref) | YES (iterator release at next iteration) | ✅ | Normal skip; iterator manages ref |
| L1922  | continue (is_visible) | YES (iterator holds ref) | YES (iterator release at next iteration) | ✅ | Normal skip |
| L1926  | implicit continue after `__scsi_remove_device` is called | YES (iterator holds ref) | YES (manual put inside `__scsi_remove_device`) + NO (iterator will release same ref again) | ❌ EXCESS PUT | Double put: body’s put + iterator’s later put |
| L1926 (condition false) | implicit continue | YES | YES (iterator release at next iteration) | ✅ | No manual put; iterator handles it |
| L1927  | loop exit (function return) after being inside `if false`/`continue` | YES (last sdev ref) | YES (iterator releases last sdev) | ✅ | Normal termination |
| L1927  | loop exit after `__scsi_remove_device` on last iteration | YES (last sdev ref) | YES (manual put) + NO (iterator releases last sdev) | ❌ EXCESS PUT | Double put on the last device |

## Analysis

- **`shost_for_each_device`** uses `__scsi_iterate_devices`, which holds an elevated reference for each `sdev` visited. The iterator releases the *previous* sdev’s reference when moving to the next, and releases the final sdev when the loop ends.
- When `__scsi_remove_device(sdev)` is called inside the loop, it performs its own `put_device` (or equivalent) on that same sdev.
- The iterator still has a saved pointer to that sdev and will call `put_device` again when it advances to the next iteration (or at loop termination). This is a clear double‑put path → `refcount excess put`.
- Even if `__scsi_remove_device` removes the device from the host’s list, the iterator’s internal pointer to the previous device remains and will be put regardless.

## Verdict

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`shost_for_each_device` holds a reference; calling `__scsi_remove_device` inside the loop drops that reference, but the iterator later drops it again → refcount excess put at function exit (line 1917).
```
