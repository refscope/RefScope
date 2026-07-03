# REAL BUG: drivers/net/wireless/realtek/rtl8xxxu/core.c:6591 rtl8xxxu_submit_int_urb()

**Confidence**: HIGH | **Counter**: `urb->kref.refcount.refs.counter`

## Reasoning

| L6586-6592 (fallthrough) | success (ret = 0) | YES (usb_anchor_urb) | YES (usb_free_urb double put) | ✅ | 2 refs held (alloc + anchor); `usb_free_urb`'s 2 puts bring count to 0 |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L6573 | error (-ENOMEM) | NO (before get) | N/A | ✅ | `usb_alloc_urb` fails, no ref held |
| L6584 → L6590 (goto error) | error (ret < 0) | YES (usb_anchor_urb at L6580) | YES (usb_unanchor_urb) + YES (usb_free_urb double put) | ❌ EXCESS PUT | unanchor drops 1 ref; `usb_free_urb` does 2 kref_puts → total 3 puts for 2 refs |
| L6586-6592 (fallthrough) | success (ret = 0) | YES (usb_anchor_urb) | YES (usb_free_urb double put) | ✅ | 2 refs held (alloc + anchor); `usb_free_urb`'s 2 puts bring count to 0 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`usb_free_urb` contract indicates two `kref_put` calls. On the error path, `usb_unanchor_urb` already drops the anchor reference, then `usb_free_urb` puts twice, causing an excess put when refcount is 0.
```
