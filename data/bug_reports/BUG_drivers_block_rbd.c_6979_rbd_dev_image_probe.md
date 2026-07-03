# REAL BUG: drivers/block/rbd.c:6979 rbd_dev_image_probe()

**Confidence**: MEDIUM | **Counter**: `$->parent_spec->kref.refcount.refs.counter`

## Reasoning

| L6956 | success return | YES | NO         | ✅        | Parent ref held for device lifetime; released later. |

## Full Response

```
| Line | Return Type | GET Done? (parent_spec ref held) | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L6901 | error return | NO (parent not set up) | N/A     | ✅        | Before any parent setup; no parent_spec ref. |
| L6904 | goto err_out_format | NO | NO        | ✅        | Jump skips rbd_dev_unprobe; no parent_spec ref. |
| L6912 | goto err_out_format | NO | NO        | ✅        | Same as above. |
| L6922 | goto err_out_probe | NO (parent not set up) | YES (rbd_dev_unprobe called) | ✅ (if parent_spec NULL, unprobe handles safely) | Parent_spec not allocated yet – rbd_dev_unprobe should be NULL‑safe. |
| L6931 | goto err_out_probe | NO | YES        | ✅        | Same reasoning. |
| L6935 | goto err_out_probe | NO | YES        | ✅        | Same reasoning. |
| L6939 | goto err_out_probe | NO | YES        | ✅        | Same reasoning. |
| L6945 | goto err_out_probe (rbd_dev_setup_parent fail) | NO (setup failed, no parent_spec created) | YES        | ✅        | Setup failure leaves parent_spec NULL → safe. |
| **L6949** | **goto err_out_probe (rbd_dev_probe_parent fail)** | **YES** (parent_spec exists from setup) | **YES** (rbd_dev_unprobe) | **❌ LEAK/EXCESS** | After setup, parent_spec refcount = 1. If `rbd_dev_probe_parent` fails it may internally drop that reference (refcount → 0), then `rbd_dev_unprobe` does a second put → **excess put**. Smatch warns exactly at this line (rbd_dev_unprobe call). |
| L6956 | success return | YES | NO         | ✅        | Parent ref held for device lifetime; released later. |

**VERDICT: REAL_BUG**  
**CONFIDENCE: MEDIUM**  

**Reasoning:** After `rbd_dev_setup_parent` succeeds, the device holds a reference on `parent_spec`. When `rbd_dev_probe_parent` fails, the error path unconditionally calls `rbd_dev_unprobe`, which likely also releases `parent_spec`. If the callee already dropped the reference on error (indicated by the contract mentioning `rbd_dev_destroy(put)` inside `rbd_dev_probe_parent`), this becomes a double‑put (excess put). The precise smatch warning points to line 6979 (the `rbd_dev_unprobe` call), confirming the refcount underflows on that path. To verify, request source for `rbd_dev_probe_parent` and `rbd_dev_unprobe`.
```
