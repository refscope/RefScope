# REAL BUG: drivers/block/drbd/drbd_receiver.c:3861 receive_SyncParam()

**Confidence**: HIGH | **Counter**: `$->local_cnt.counter`

## Reasoning

ne 3789 followed by `goto disconnect`. The `disconnect` label (line 3847‑3860) unconditionally does `if (new_disk_conf) { put_ldev(device); ... }`. After the first put, `new_disk_conf` still holds the pointer, so the second `put_ldev` executes → excess refcount decrement on `$->local_cnt.counter`.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 3671 | return config_unknown_volume | NO (before get) | N/A  | ✅ | |
| 3683 | return -EIO (size check) | NO (before get) | N/A  | ✅ | |
| 3706 | return err (drbd_recv_all header) | NO (before get) | N/A  | ✅ | |
| 3716 | return -ENOMEM (kzalloc fail) | YES | YES (put at 3713, then return) | ✅ | get_ldev succeeded, then put and return |
| 3730 | goto reconnect (data_size error) | YES (new_disk_conf may be non-NULL) | NO (reconnect label does put at 3841) | ✅ | |
| 3735 | goto reconnect (drbd_recv_all fail) | YES (if get succeeded) | NO (reconnect label does put) | ✅ | |
| 3754 | goto disconnect (verify alg mismatch at WF_REPORT_PARAMS) | YES (if get succeeded) | NO (disconnect label does put at 3850) | ✅ | |
| 3760 | goto disconnect (IS_ERR verify_tfm) | YES | NO (disconnect does put) | ✅ | |
| 3768 | goto disconnect (csums alg mismatch at WF_REPORT_PARAMS) | YES | NO (disconnect does put) | ✅ | |
| 3774 | goto disconnect (IS_ERR csums_tfm) | YES | NO (disconnect does put) | ✅ | |
| 3789-3790 | goto disconnect after put_ldev (fifo_alloc fail) | YES (get succeeded, new_disk_conf true) | YES (first put at line 3789), but then disconnect label does **second put at line 3850** → EXCESS PUT | ❌ **REAL_BUG** | double put because new_disk_conf not set to NULL after first put |
| 3798 | goto disconnect (kzalloc new_net_conf fail) | YES (if new_disk_conf) | NO (disconnect does put) | ✅ | |
| 3837 | return 0 (success) | YES (if new_disk_conf) | YES (put at 3822) | ✅ | |
| 3845 | return -EIO (reconnect) | YES (if new_disk_conf) | YES (put at 3841) | ✅ | |
| 3860 | return -EIO (disconnect) | YES (if new_disk_conf, except the double‑put path) | YES (put at 3850, unless already put) | ✅ *except* path 3789 | *disconnect normally works, but on the double‑put path it releases twice* |

**Double‑put path**: `put_ldev(device)` at line 3789 followed by `goto disconnect`. The `disconnect` label (line 3847‑3860) unconditionally does `if (new_disk_conf) { put_ldev(device); ... }`. After the first put, `new_disk_conf` still holds the pointer, so the second `put_ldev` executes → excess refcount decrement on `$->local_cnt.counter`.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`put_ldev` at L3789 before `goto disconnect` is not guarded by clearing `new_disk_conf`, causing a second `put_ldev` inside the `disconnect` label (L3850) — double put.
```
