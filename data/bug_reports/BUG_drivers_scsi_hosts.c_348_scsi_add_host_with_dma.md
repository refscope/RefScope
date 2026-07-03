# REAL BUG: drivers/scsi/hosts.c:348 scsi_add_host_with_dma()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L348 | fail return error | (any of the above) | (any of the above) | (any of the above) | (any of the above) | (depends) | common error return |

## Full Response

```
| Line | Return Type | GET Done? (parent) | GET Done? (shost_gendev) | PUT Done? (parent) | PUT Done? (shost_gendev) | Balanced? | Notes |
|------|-------------|--------------------|--------------------------|--------------------|--------------------------|-----------|-------|
| L230 | goto fail | NO (before gets) | NO | N/A | N/A | ✅ | |
| L235 | goto fail | NO | NO | N/A | N/A | ✅ | |
| L240 | goto fail | NO | NO | N/A | N/A | ✅ | |
| L253 | goto fail | NO | NO | N/A | N/A | ✅ | |
| L276 | goto out_disable_runtime_pm | NO (before gets) | NO | N/A | N/A | ✅ | device_add(shost_gendev) failed |
| L285 | goto out_del_gendev | YES | YES | NO | NO | ❌ LEAK | `get_device(parent)` at L280, `get_device(&shost_gendev)` at L284. Path: out_del_gendev → out_disable_runtime_pm → fail. No put for either. |
| L290 | goto out_del_dev (kzalloc fail) | YES | YES | NO | NO | ❌ LEAK | out_del_dev → out_del_gendev → out_disable_runtime_pm → fail |
| L299 | goto out_del_dev (work_q fail) | YES | YES | NO | NO | ❌ LEAK | out_del_dev → out_del_gendev → ... |
| L308 | goto out_del_dev (sysfs fail) | YES | YES | NO | NO | ❌ LEAK | out_del_dev → out_del_gendev → ... |
| L313 | goto out_del_dev (pseudo fail) | YES | YES | NO | NO | ❌ LEAK | out_del_dev → out_del_gendev → ... |
| L319 | success return 0 | YES | YES | (held for lifetime, to be released by scsi_remove_host / release) | ⚠️ not freed here, but may be balanced later | Success path uses probe‑get/remove‑put pattern (see point 6), so not counted as bug. |
| L348 | fail return error | (any of the above) | (any of the above) | (any of the above) | (any of the above) | (depends) | common error return |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

The function calls unconditional get_device() twice (parent and shost_gendev) but all error paths after L285 (device_add(shost_dev) failure) and subsequent allocations/setup failures (out_del_dev) omit put_device() for these references. The cleanup labels only put_device(&shost->shost_dev) and do device_del() on shost_gendev, never releasing the extra references taken on shost_gendev and its parent via get_device. This causes a refcount leak on the kref of those devices (seen by smatch at the final return line). The success path may defer release to the host removal code, but the error paths must explicitly drop the references.
```
