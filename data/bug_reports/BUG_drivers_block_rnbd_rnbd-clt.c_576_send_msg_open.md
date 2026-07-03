# REAL BUG: drivers/block/rnbd/rnbd-clt.c:576 send_msg_open()

**Confidence**: HIGH | **Counter**: `$->busy.counter`

## Reasoning

→ One `get`, two `put`s on same error path → refcount underflow / excess put, matching the warning on `busy.counter`.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L545 | error return (rsp NULL) | N/A | N/A | ✅ | before rnbd_get_iu |
| L550 | error return (iu == NULL) | NO (get failed) | N/A | ✅ | iu NULL, no ref held |
| L567-569 + L574 (error path) | return err (non-zero) | YES (successful get) | YES — once at L568 (PUT1), once at L574 (PUT2) | ❌ EXCESS PUT | **Double-put** — one get, two puts on error |
| L571 + L574 (success path) | return err (0) | YES | YES (once at L574) | ✅ | normal release |

**Path analysis:**
- `rnbd_get_iu()` succeeds, reference taken.
- On error from `send_usr_msg()`, the `if (err)` block calls `rnbd_put_iu(sess, iu)` (line 568), then execution falls through to the unconditional `rnbd_put_iu(sess, iu)` (line 574).  
  → One `get`, two `put`s on same error path → refcount underflow / excess put, matching the warning on `busy.counter`.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Double‑put of `iu` on the `send_usr_msg()` error path: `rnbd_put_iu()` is called inside the `if (err)` block and again unconditionally afterwards.
```
