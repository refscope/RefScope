# REAL BUG: net/netfilter/nft_tproxy.c:80 nft_tproxy_eval_v4()

**Confidence**: LOW | **Counter**: `$->sk_refcnt.refs.counter`

## Reasoning

ithout the source of `nf_tproxy_handle_time_wait4` the exact behaviour is unknown, but the warning strongly suggests the second scenario: the final `nf_tproxy_sk_is_transparent` (line ~80) is doing an extra put because `handle_time_wait4` already released the reference without providing a new one.

## Full Response

```
[NEED_SOURCE] nf_tproxy_handle_time_wait4

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L33 (after tprot/fragoff check) | return | NO (no get yet) | N/A | ✅ | |
| L42 (after skb_header_pointer fail) | return | NO | N/A | ✅ | |
| L67–L69 (sk && TCP_TIME_WAIT) | branch to handle_time_wait4 → final if | YES (from ESTABLISHED get) → unknown after handle_time_wait4 | PUT by nf_tproxy_sk_is_transparent or ownership transfer | ⚠️ UNCLEAR | handle_time_wait4 may release the ESTABLISHED ref and return a new/different sk with ref – if it fails to properly account refs, the final put (via nf_tproxy_sk_is_transparent if not transparent) may double-put or release a ref not held, triggering excess put. |
| L71–L73 (!sk → LISTENER get) | branch to LISTENER get → final if | YES (LISTENER get) | PUT by nf_tproxy_sk_is_transparent if not transparent, or assign_sock if transparent | ✅ (assuming get returns ref) | If LISTENER get succeeds and nf_tproxy_sk_is_transparent conditionally puts correctly, balanced. |
| L66–L75 (sk && state != TCP_TIME_WAIT) | branch directly to final if | YES (ESTABLISHED get) | PUT by nf_tproxy_sk_is_transparent or assign_sock | ✅ | Ref held from ESTABLISHED get; final if will either put (if not transparent) or transfer (if transparent). Balanced. |

**KEY UNKNOWN**: In the TCP_TIME_WAIT path, `nf_tproxy_handle_time_wait4()` is called with the already‑referenced `sk`. It may:
- Release the original ref (sock_put) and return a new socket with its own ref → balanced (final if handles the new ref).
- Release the original ref and return the same `sk` pointer *without* re‑incrementing → the caller then has a dangling ref, and any later put (e.g., by `nf_tproxy_sk_is_transparent` when not transparent) would underflow, causing the observed **refcount excess put**.
- Or some other mismanagement.

Without the source of `nf_tproxy_handle_time_wait4` the exact behaviour is unknown, but the warning strongly suggests the second scenario: the final `nf_tproxy_sk_is_transparent` (line ~80) is doing an extra put because `handle_time_wait4` already released the reference without providing a new one.

VERDICT: REAL_BUG
CONFIDENCE: LOW (requires verification of nf_tproxy_handle_time_wait4’s ref handling)

--- [NEED_SOURCE r1] ---

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L33 (no sk lookup yet) | early return | NO | N/A | ✅ | |
| L42 (skb_header_pointer fail) | return | NO | N/A | ✅ | |
| L67–L69 (TCP_TIME_WAIT → handle_time_wait4 returns sk, later final if) | final if/return | YES (ESTABLISHED get) but then **consumed** by handle_time_wait4. If no listener found, returned TIME_WAIT socket has **no reference** from caller. | If `nf_tproxy_sk_is_transparent` returns false, it calls `sock_put(sk)` – but caller owns no ref → underflow. If true, `assign_sock` expects a ref → bug
```
