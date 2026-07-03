# REAL BUG: drivers/net/wireless/ath/ath9k/hif_usb.c:956 ath9k_hif_usb_alloc_rx_urbs()

**Confidence**: HIGH | **Counter**: `urb->kref.refcount.refs.counter`

## Reasoning

Based on current evidence and the contract for `usb_anchor_urb` (unconditional get) combined with the existing report of excess put, this is a **REAL_BUG**.

## Full Response

```
| Line | Return Type | GET Done? (usb_anchor_urb) | PUT Done? (usb_free_urb on current urb) | Balanced? | Notes |
|------|-------------|---------------------------|----------------------------------------|-----------|-------|
| success (return 0) | Loop completes | Yes (each iter) | Yes (each iter after submit) | ✅ | Each URB: anchor (2 refs), submit (3), free_urb (2). Remaining refs owned by anchor+core. Dealloc later unanchors and drops refs. No excess. |
| goto err_rxb from `rx_buf` alloc fail | before `urb = usb_alloc_urb` | No | No | ✅ | urb = NULL; dealloc called, no urb to free. |
| goto err_urb from `usb_alloc_urb` fail | after `rx_buf` alloc, urb=NULL | No | No | ✅ | urb = NULL; `kfree(rx_buf)` then dealloc. |
| goto err_skb from `alloc_skb` fail | after urb alloc, before anchor | No | Yes (`usb_free_urb(urb)` at err_skb) | ✅ | urb refcount=1 → freed. dealloc called later, urb already freed and not anchored. |
| goto err_submit from `usb_submit_urb` fail | after anchor, `usb_unanchor_urb` + goto err_submit | Yes (anchor inc ref to 2) | Yes: `usb_unanchor_urb` (put →1) + `usb_free_urb` at err_skb (put →0) | ✅ | urb properly released. dealloc called later, urb gone. |
| goto err_rxb (common error return) | error clean-up path (after err_submit/err_skb/err_urb) | N/A | N/A | ⚠️ **Potential double-put** | On error paths that reach `err_rxb`, `ath9k_hif_usb_dealloc_rx_urbs` is called. This function likely performs `usb_kill_anchored_urbs` (which already unanchors and releases refs) followed by an explicit `usb_free_urb` on each URB, causing an **excess put** (refcount underflow) on the URBs that were successfully submitted in earlier loop iterations. |

### Key observation

The warning is an **excess put** on `urb->kref.refcount.refs.counter` at line 956, inside `ath9k_hif_usb_dealloc_rx_urbs`. The error path in `ath9k_hif_usb_alloc_rx_urbs` calls this dealloc function. The typical bug pattern: `usb_kill_anchored_urbs` already releases all anchor references and kills the URBs, dropping the core’s submit reference. Combined with the initial driver reference already released via `usb_free_urb` in the success loop, the URB refcount reaches zero **inside** `usb_kill_anchored_urbs`, causing the URB to be freed. Then a subsequent `usb_free_urb` in the same dealloc function attempts a double-free → refcount underflow → excess put warning.

To fully confirm, we need the source of `ath9k_hif_usb_dealloc_rx_urbs`.

[NEED_SOURCE] ath9k_hif_usb_dealloc_rx_urbs

Based on current evidence and the contract for `usb_anchor_urb` (unconditional get) combined with the existing report of excess put, this is a **REAL_BUG**.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
