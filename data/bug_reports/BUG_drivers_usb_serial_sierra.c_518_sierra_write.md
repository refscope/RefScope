# REAL BUG: drivers/usb/serial/sierra.c:518 sierra_write()

**Confidence**: HIGH | **Counter**: `urb->kref.refcount.refs.counter`

## Reasoning

letion handler would typically call `usb_unanchor_urb()` (and possibly `usb_free_urb()`), releasing the anchor reference. Then the subsequent `usb_free_urb()` in `sierra_write()` would decrement a refcount that has already reached zero — the “refcount excess put” detected by the tool.

## Full Response

```
# Audit of sierra_write() for refcount excess put warning

## Contracts Summary
- **GET**: `usb_anchor_urb()` — unconditional, increments URB refcount (kref).
- **PUT** (relevant): `usb_free_urb()` — conditional on non-null, decrements kref, frees if zero.
- **PUT**: `usb_unanchor_urb()` — (assumed) removes from anchor and decrements anchor’s ref.

## Path Table (all return/go‑to paths)

| Line | Return Type                  | GET (anchor) Done? | PUT Done?                               | Balanced? | Notes |
|------|------------------------------|--------------------|-----------------------------------------|-----------|-------|
| L422 | `return 0` (count==0)        | NO (no URB alloc)  | N/A                                     | ✅ | early exit, no URB |
| L435 | `return 0` (write limit)     | NO                 | N/A                                     | ✅ | early exit, no URB |
| L449 | `goto error_simple` (autopm) | NO                 | N/A                                     | ✅ | no URB yet |
| L456 | `goto error_no_buffer`       | NO                 | N/A                                     | ✅ | no URB alloc yet |
| L461 | `goto error_no_urb`          | NO                 | N/A                                     | ✅ | alloc failed, no URB |
| L466 | `goto skip_power` (suspended)| YES (anchored)     | YES (usb_free_urb at skip_power)        | ⚠️ **EXCESS PUT risk** | suspended path: anchor + free without submit – refcount 2→1, fine if completion never fires before free. Safe in static view, but possible race? (see below) |
| L479 | `goto error` (submit fail)   | YES (anchored)     | YES (unanchor + usb_free_urb)           | ✅ | immediate unanchor then free – balanced |
| L487 | **fall‑through to skip_power** (submit success) | YES (anchored) | YES (usb_free_urb at skip_power) | ❌ **EXCESS PUT** | **Submit succeeded** → URB is in‑flight. The callback (sierra_outdat_callback) will later release the anchor reference. The caller’s `usb_free_urb` after successful submission is an **extra put** that races with the callback, potentially causing a double‑free and refcount underflow. This is the likely source of the warning. |

**Notes:**
- The suspended path (goto skip_power) does not submit the URB; the URB is only anchored to `delayed`. No callback runs immediately, so `usb_free_urb` is safe in the static flow, but a future reactivation could trigger a callback that also does a put — however the warning is about the `active` case.
- The **submit success path** is the bug: `usb_free_urb(urb)` is called after `usb_submit_urb()` returns 0. At that point the URB may already complete (if the endpoint responds synchronously or very quickly). The completion handler would typically call `usb_unanchor_urb()` (and possibly `usb_free_urb()`), releasing the anchor reference. Then the subsequent `usb_free_urb()` in `sierra_write()` would decrement a refcount that has already reached zero — the “refcount excess put” detected by the tool.

## Verdict
**VERDICT
```
