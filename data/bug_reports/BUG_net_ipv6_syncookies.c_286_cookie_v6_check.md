# REAL BUG: net/ipv6/syncookies.c:286 cookie_v6_check()

**Confidence**: HIGH | **Counter**: `skb->users.refs.counter`

## Reasoning

4. **goto out between GET and PUT?** The `out_drop` label is reached via `goto out_drop` from L255, after the GET. The `out_drop` label only contains `sk_skb_reason_drop(sk, skb, reason); return NULL;` — **no** release of the extra ref.

## Full Response

```
## Source Request

[NEED_SOURCE] reqsk_free
[NEED_SOURCE] tcp_get_cookie_sock

**Why required**: The `reqsk_free` function determines whether the `out_free` path (dst lookup failure) properly releases the extra skb reference stored in `ireq->pktopts`. However, the primary leak is on the `out_drop` path after `tcp_get_cookie_sock` failure, where `req` is neither freed nor its pktopts reference released. These sources confirm whether `out_free` is also affected, but do not change the verdict for `out_drop`.

## Path Table

| Line | Return Type       | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------------|-----------|-----------|-----------|-------|
| L182 | goto out          | NO        | N/A       | ✅        | Syncookies disabled or not ACK/RST |
| L194 | IS_ERR(req) goto out | NO     | N/A       | ✅        | req error before GET |
| L197 | !req → goto out_drop | NO    | N/A       | ✅        | Drop original skb (caller’s ref); no GET |
| L205 | security hook → goto out_free | NO | N/A | ✅       | Before GET |
| L237 | IS_ERR(dst) → goto out_free | YES | **uncertain** | **?** | `refcount_inc` executed; `out_free` calls `reqsk_free(req)`. If `reqsk_free` releases `pktopts`, extra ref is released; otherwise LEAK. |
| L255 | tcp_get_cookie_sock fails → goto out_drop | YES | NO   | ❌ **LEAK** | `refcount_inc` done; `out_drop` only drops one reference (`sk_skb_reason_drop`). The extra reference held by `req->pktopts` is never released; `req` is also leaked. |
| L258 | out: return ret   | YES | YES* | ✅        | `tcp_get_cookie_sock` succeeded; ownership of `req` (and pktopts ref) transferred to child socket; eventual release on child destruction. |

**Critical observation**: The `out_drop` path at L255 is reachable after `refcount_inc`. It calls `sk_skb_reason_drop(sk, skb, reason)`, which releases **one** reference (the original caller’s reference). The extra reference from `refcount_inc` (held by `ireq->pktopts`) is never released because `reqsk_free(req)` is not called on this path. This results in a refcount leak of `skb->users.refs.counter` and a memory leak of `req`. The warning location (L286, the final `return NULL;` of `out_drop`) matches this imbalance.

## Pre-Verdict Checklist

1. **“Held for device lifetime”?** Not applicable.
2. **“Ownership transferred”?** Only on the success path (L258) where `tcp_get_cookie_sock` takes ownership of `req`. There is **no** ownership transfer on the error path that jumps to `out_drop`; `req` is never consumed.
3. **Unconditional GET?** `refcount_inc` is unconditional. After it executes, **every** return must either release the extra reference or transfer it to a valid owner. The `out_drop` path does neither.
4. **goto out between GET and PUT?** The `out_drop` label is reached via `goto out_drop` from L255, after the GET. The `out_drop` label only contains `sk_skb_reason_drop(sk, skb, reason); return NULL;` — **no** release of the extra ref.

## VERDICT: REAL_BUG

CONFIDENCE: HIGH

`refcou
```
