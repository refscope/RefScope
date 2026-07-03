# REAL BUG: drivers/nvme/target/loop.c:645 nvme_loop_create_ctrl()

**Confidence**: HIGH | **Counter**: `ctrl->ctrl.device.kobj.kref.refcount.refs.counter`

## Reasoning

| L? (nvme_loop_create_io_queues fail) | goto out_remove_admin_queue → out_free_queues → out_uninit_ctrl → falls through | YES | YES (2x) | ❌ EXCESS PUT | same double‑put chain |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L566 | error       | NO (before any get) | N/A  | ✅ | kzalloc failed, no refs |
| L575 | goto out    | NO (before nvme_add_ctrl) | NO  | ✅ | nvme_init_ctrl fail, no ref held |
| L580 | goto out_put_ctrl | YES (nvme_add_ctrl always incs) | YES (once, nvme_put_ctrl) | ✅ | direct put, no uninit |
| L599 | success     | YES | NO (ref transferred to caller) | ✅ | returns ctrl with ref held |
| L? (queues alloc fail) | goto out_uninit_ctrl → falls through | YES | YES (2x: nvme_uninit_ctrl + nvme_put_ctrl) | ❌ EXCESS PUT | nvme_uninit_ctrl already calls nvme_put_ctrl, then extra nvme_put_ctrl |
| L? (nvme_loop_configure_admin_queue fail) | goto out_free_queues → out_uninit_ctrl → falls through | YES | YES (2x) | ❌ EXCESS PUT | same double‑put chain |
| L? (nvme_loop_create_io_queues fail) | goto out_remove_admin_queue → out_free_queues → out_uninit_ctrl → falls through | YES | YES (2x) | ❌ EXCESS PUT | same double‑put chain |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`nvme_uninit_ctrl` already calls `nvme_put_ctrl`, but error paths that jump to `out_uninit_ctrl` (or later labels) fall through into an explicit `nvme_put_ctrl` at `out_put_ctrl`, resulting in a double put and the reported refcount excess.
```
