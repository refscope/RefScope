# REAL BUG: net/bluetooth/rfcomm/core.c:500 __rfcomm_dlc_close()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

If `__rfcomm_dlc_close` is called on a DLC that was never added to a session list (or already unlinked), the put over-decrements the counter, causing the reported "refcount excess put". There is no guard (e.g., checking `d->session` or a link flag) before `rfcomm_dlc_unlink` in this path.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L456 | early return | NO (before any get) | NO | ✅ | session NULL, safe |
| L464-470 (inside first switch) | return 0 after rfcomm_schedule() | NO | NO | ✅ | DEFER_SETUP handled, no ref ops |
| L475 (BT_CONNECT/BT_CONNECTED) → break → L497 return 0 | return 0 | ? (calls `__rfcomm_dlc_disconn`, unknown GET) | NO | ? | If disconn does a get, no put here; but that get is for disconnect lifecycle, not a leak |
| L479-482 (BT_CONFIG, s->state != BT_BOUND) → break → L497 return 0 | return 0 | ? (calls `__rfcomm_dlc_disconn`) | NO | ? | Same as above |
| L485-496 (default, inc. BT_CONFIG BT_BOUND) | return 0 | NO (function does no get) | ⚠️ YES — `rfcomm_dlc_clear_timer` (conditional) + `rfcomm_dlc_unlink` (unconditional put) | ❌ EXCESS PUT | This path does up to two puts without a preceding get inside the function. If the DLC was never linked, or already unlinked, `rfcomm_dlc_unlink`’s unconditional put will drop a reference not held → excess put. |

⚠️ The default path (which includes falling through from `BT_CONFIG` when `s->state == BT_BOUND`) calls `rfcomm_dlc_unlink()`, which is an unconditional `rfcomm_dlc_put`.  
If `__rfcomm_dlc_close` is called on a DLC that was never added to a session list (or already unlinked), the put over-decrements the counter, causing the reported "refcount excess put". There is no guard (e.g., checking `d->session` or a link flag) before `rfcomm_dlc_unlink` in this path.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__rfcomm_dlc_close()` default path unconditionally calls `rfcomm_dlc_unlink()` (unconditional put) without verifying the DLC holds a reference from being linked; an already unlinked or never-linked DLC leads to an excess put.
```
