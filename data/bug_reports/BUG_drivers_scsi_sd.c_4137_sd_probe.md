# REAL BUG: drivers/scsi/sd.c:4137 sd_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L4137 (scsi_autopm_put_device + return error) | error return | depends on path | inconsistent on out_free_index path | ❌ | missing put of parent from get_device |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L4003 (type check) | goto out | NO | N/A | ✅ | Before get_device |
| ~L4006 (ZBC unsupported) | goto out | NO | N/A | ✅ | Before get_device |
| ~L4013 | goto out | NO | N/A | ✅ | Before get_device |
| ~L4021 (kzalloc fail) | goto out | NO | N/A | ✅ | Before get_device |
| ~L4026 (blk_mq_alloc_disk_for_queue fail) | goto out_free | NO | N/A | ✅ | Before get_device |
| ~L4028 (ida_alloc fail) | goto out_put | NO | N/A | ✅ | Before get_device |
| ~L4033 (sd_format_disk_name fail) | goto out_free_index | NO | N/A | ✅ | Before get_device |
| ~L4071 (device_add fail) | put_device + put_disk → goto out | YES | YES (via put_device on disk_dev) | likely ✅ | disk_dev release should put parent; if missing, separate bug |
| ~L4091 (sector_size > PAGE_SIZE, sd_large_pool_create fail) | goto out_free_index | YES | NO | ❌ LEAK | disk_dev already registered, never unregistered, parent ref leaked |
| ~L4097 (device_add_disk fail) | device_unregister + put_disk → goto out | YES | YES (via device_unregister) | ✅ | |
| ~L4144 (success) | return 0 | YES | deferred to disk_dev removal | ✅ | parent held by disk_dev lifetime |
| L4137 (scsi_autopm_put_device + return error) | error return | depends on path | inconsistent on out_free_index path | ❌ | missing put of parent from get_device |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`out_free_index` path after successful `device_add` leaks the reference acquired via `get_device(dev)` because it never calls `device_unregister` or `put_device` on `&sdkp->disk_dev`.
```
