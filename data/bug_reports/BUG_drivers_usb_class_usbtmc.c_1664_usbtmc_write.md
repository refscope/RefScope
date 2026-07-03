# REAL BUG: drivers/usb/class/usbtmc.c:1664 usbtmc_write()

**Confidence**: HIGH | **Counter**: `urb->kref.refcount.refs.counter`

## Reasoning

is called → the URB’s completion handler (`usbtmc_write_bulk_cb`) frees the URB (drops the anchor’s reference and the remaining refcount) → execution reaches the `exit` label → `usb_free_urb(urb)` is called on a stale/dangling urb, causing an extra kref_put and triggering the “excess put” warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1538 | goto exit   | NO (before urb alloc) | N/A  | ✅ | urb=NULL, usb_free_urb is nop |
| L1550 | goto exit   | NO (before urb alloc) | N/A  | ✅ | urb=NULL |
| L1556 | goto exit   | NO (before urb alloc) | N/A  | ✅ | urb=NULL |
| L1565 | goto exit   | NO (alloc fail) | N/A  | ✅ | urb=NULL |
| L1610 | goto exit   | NO (before anchor) | YES (usb_free_urb) | ✅ | single creation ref released |
| L1630 | goto exit (submit error) | YES (anchor) | YES (unanchor? then usb_free_urb) | ⚠️ | see note below |
| L1645 | goto exit (generic_write failure) | YES (anchor) | YES (usb_kill_anchored_urbs frees URB, then usb_free_urb again) | ❌ EXCESS PUT | double free |
| L1655 | return done (success) | YES (anchor) | YES (usb_free_urb releases caller’s ref) | ✅ | anchor ref will be dropped later by completion |

**Key for L1630 (submit error)**: If `usb_unanchor_urb` does not put the anchor’s reference, this path **leaks** a ref, not an excess put. The warning is specifically about an excess put, so it is triggered on L1645, not here.

**Path L1645** – `usbtmc_generic_write` returns <0 → `usb_kill_anchored_urbs` is called → the URB’s completion handler (`usbtmc_write_bulk_cb`) frees the URB (drops the anchor’s reference and the remaining refcount) → execution reaches the `exit` label → `usb_free_urb(urb)` is called on a stale/dangling urb, causing an extra kref_put and triggering the “excess put” warning.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`usbtmc_write` calls `usb_kill_anchored_urbs` on error, which frees the URB, then the subsequent `usb_free_urb` at `exit` double-frees the URB, causing a refcount excess put on line 1664.
```
