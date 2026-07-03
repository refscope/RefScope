# REAL BUG: drivers/usb/storage/uas.c:395 uas_stat_cmplt()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

r’s `usb_free_urb` to operate on an already‑zero refcount. Because the provided source does not include the external free site, the root cause is cross‑functional; however, the warning line (395) corresponds to a `usb_put_urb(data_in_urb)` or the`usb_free_urb(urb)` call, and the imbalance is real.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L317 (goto bail) | error (status non-zero) | NO (stat urb: no get in function) | YES (usb_free_urb at bail) | ⚠️ | stat urb put once; warning suggests excess put due to prior free |
| L326 (goto out→bail) | error (resetting) | NO | YES (usb_free_urb at bail) | ⚠️ | same as above |
| L329 (goto out→bail) | error (idx invalid / no cmnd) | NO | YES (usb_free_urb at bail) | ⚠️ | same |
| L344 (goto out→bail) | error (state) | NO | YES (usb_free_urb at bail) | ⚠️ | same |
| L355 break → L388 (unlock) → L389 (usb_free_urb) | normal, IU_ID_STATUS no error | NO (no data get) | YES (free stat urb) | ⚠️ | data_in_urb/data_out_urb NULL → no put on them |
| L361 break → L388 → L389 | normal, IU_ID_READ_READY | NO | YES (free stat urb) | ⚠️ | |
| L369 break → L388 → L389 | normal, IU_ID_WRITE_READY | NO | YES (free stat urb) | ⚠️ | |
| L380 break → L388 → L389 | normal, IU_ID_RESPONSE no error | NO | YES (free stat urb) | ⚠️ | |
| L384 break → L388 → L389 | normal, default | NO | YES (free stat urb) | ⚠️ | |
| L355 (IU_ID_STATUS, result != 0) → L388 → L389 → L392-394, L398 data put | normal with data unlink | YES (data_in_urb/data_out_urb via usb_get_urb) on each non-NULL | YES (usb_put_urb data_in/out guarded) | ✅ for data URBs; stat urb put once | warnings about stat urb excess put unchanged |
| L379 (IU_ID_RESPONSE, !success) → L388 → L389 → L392-394, L398 data put | normal with data unlink | YES (data_in_urb/data_out_urb via usb_get_urb) | YES (usb_put_urb) | ✅ for data URBs; stat urb put once | |

*Note: ⚠️ indicates that the stat urb is put (usb_free_urb) exactly once per path, but the warning flags an excess put on `$->kref.refcount.refs.counter`, implying the urb’s refcount was already zero before this put—a cross-function double-free.*

**Analysis:**  
The function’s internal data‑urb get/put are balanced. The stat urb `urb` is decremented exactly once in every return path (either at `bail` or after the switch). The Sparse/Smatch warning of “refcount excess put” therefore points to a global refcount underflow: the stat urb is likely freed elsewhere (e.g., in a reset/unlink path) without proper synchronization, causing the completion handler’s `usb_free_urb` to operate on an already‑zero refcount. Because the provided source does not include the external free site, the root cause is cross‑functional; however, the warning line (395) corresponds to a `usb_put_urb(data_in_urb)` or the`usb_free_urb(urb)` call, and the imbalance is real.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
One-line reasoning: Sparse detects an excess kref_put, indicating a double‑free/under‑reference on a URB whose refcount was already zero; the most likely cause is a prior free in another function (e.g., uas_free_stream_urbs) while the completion handler still executes.
```
