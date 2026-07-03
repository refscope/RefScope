# REAL BUG: drivers/net/wireless/ath/ath9k/hif_usb.c:132 hif_usb_send_regout()

**Confidence**: HIGH | **Counter**: `urb->kref.refcount.refs.counter`

## Reasoning

he `usb_free_urb(L125)` drops a reference while the URB still has active references (anchor, HCD). When the completion callback later calls `usb_put_urb`/`usb_free_urb`, the second put on an already-released reference causes a refcount underflow, matching the “refcount excess put” warning.

## Full Response

```
## Path Table

| Line(s)         | Return Type       | GET Done?                                      | PUT Done?              | Balanced? | Notes                                                                                                     |
|-----------------|-------------------|------------------------------------------------|------------------------|-----------|-----------------------------------------------------------------------------------------------------------|
| L107            | error (return)    | NO (urb alloc failed)                          | N/A                    | ✅         | No urb, nothing to balance.                                                                               |
| L112            | error (return)    | YES (alloc ref only)                           | YES (usb_free_urb L111)| ✅         | Matches allocation ref; no anchor GET, so balanced.                                                        |
| L127 (via L121) | error (ret != 0)  | YES (alloc + anchor GETs)                      | YES (usb_free_urb L125)but only 1 PUT for 2 GETs | ❌ LEAK    | Implicit leaves ref count > 0; not an excess put. Leak path but warning is about L125 in success case.    |
| L127 (via L120) | success (ret == 0)| YES (alloc + anchor + possible submit GETs) | YES (usb_free_urb L125)but this is an invalid early put | ❌ EXCESS PUT (BUG) | **After successful submit, the URB is in‑flight; the function must NOT call usb_free_urb.** The callback will later do its own put, causing a double‑kref_put and refcount underflow → excess put at L125 (actual offset may vary, original warning at L132). |

**🔴 LEAK on error path (submit failure)**: The `usb_unanchor_urb` does **not** release the anchor’s kref; the `usb_free_urb` only releases one reference, leaving the anchor reference leaked.  
**🔴 EXCESS PUT on success path**: The `usb_free_urb(L125)` drops a reference while the URB still has active references (anchor, HCD). When the completion callback later calls `usb_put_urb`/`usb_free_urb`, the second put on an already-released reference causes a refcount underflow, matching the “refcount excess put” warning.

---

## VERDICT: REAL_BUG  
**CONFIDENCE: HIGH**  

`usb_free_urb(urb)` after a successful `usb_submit_urb` releases a reference that must be held by the completion handler, leading to a future double‑kref_put and refcount underflow. The function should only free the URB in the error path (after submit failure and unanchor).
```
