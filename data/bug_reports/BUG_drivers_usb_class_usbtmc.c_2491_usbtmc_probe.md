# REAL BUG: drivers/usb/class/usbtmc.c:2491 usbtmc_probe()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

**Therefore, REAL_BUG.**

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2393 (if !data) | return -ENOMEM | No (before kref_init) | N/A | ✅ | Allocation failed, no refcount |
| L2418 (goto err_put, after usb_find_common_endpoints) | error | YES (kref_init) | YES (err_put does kref_put) | ✅ | Only initial ref to drop |
| L2423 (goto err_put, after wMaxPacketSize check) | error | YES | YES | ✅ | Only initial ref |
| L2441 (goto error_register, !data->iin_urb) | error | YES (kref_init only) | YES (usbtmc_free_int+err_put kref_put) | ✅ | iin_urb alloc failed, no extra ref |
| L2449 (goto error_register, after kref_get, !iin_buffer) | error | YES (kref_init + kref_get) | NO (only 1 kref_put via err_put) | ❌ LEAK | kref_get added an extra ref; usbtmc_free_int likely does not put it |
| L2465 (goto error_register, usb_submit_urb failed) | error | YES (kref_init + kref_get) | NO | ❌ LEAK | Same as above, urb submit failure after extra get |
| L2479 (goto error_register, usb_register_dev failed) | error | conditional: if iin_ep_present → kref_init + kref_get (YES), else → kref_init only (YES) | Depends: if intr ref present → NO extra put, else OK | ❌ LEAK when intr ref held | |
| L2482 (return 0) | success | YES (kref_init + possibly kref_get) | NO immediate put; cleanup deferred to disconnect | ✅ (by design) | Success path, refs managed by device lifecycle |

**Pre-verdict checklist:**

1. **"Held for device lifetime"?** Yes, but error paths inside probe (before success) must release all acquired references. The error_register/err_put paths do not release the extra kref_get.
2. **"Ownership transferred"?** No; interrupt urb hold is a reference held for the lifetime of the urb. On error, the urb is freed but the reference is not dropped.
3. **Unconditional GET?** `kref_get` is unconditional. Any error return after it must put.
4. **goto out between GET and PUT?** `goto error_register` after `kref_get` leads to `usbtmc_free_int` + `kref_put` (err_put). Only one `kref_put` executed — insufficient for two refs.

**Therefore, REAL_BUG.**

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`kref_get` adds an extra reference at line ~2447; three `goto error_register` paths after that (L2449, L2465, L2479) only perform one `kref_put` at `err_put`, leaking the interrupt protection reference because `usbtmc_free_int` does not drop it.
```
