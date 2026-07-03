# REAL BUG: net/netfilter/xt_TPROXY.c:81 tproxy_tg4()

**Confidence**: LOW | **Counter**: `$->sk_refcnt.refs.counter`

## Reasoning

These are essential to verify reference handling, particularly whether `nf_tproxy_handle_time_wait4` consumes the original sk reference and whether the missing code contains an extra put.

## Full Response

```
## Path Table for `tproxy_tg4()` (based on provided lines 36-69)

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 46  | error (hp==NULL) | NO (before any get) | N/A | ✅ | `nf_tproxy_get_sock_v4` never called |
| 65  | success (NF_ACCEPT) | YES | YES (consumed) | ✅ | sk from get, `nf_tproxy_sk_is_transparent` returned true → kept ref, then `nf_tproxy_assign_sock` consumes it (ownership transfer) |
| 68  | error (NF_DROP) | YES (if sk) but PUT if not transparent | YES (via `nf_tproxy_sk_is_transparent` when false) | ✅ | When sk != NULL and not transparent, `nf_tproxy_sk_is_transparent` calls `sock_gen_put` (conditional PUT). Reference then gone. |

## 🔴 Missing Source

The provided main function ends at line 69, but the warning references `line 81`. This line is not included in the code snippet, so there may be additional return paths or a different execution context inside `tproxy_tg4()` that could cause an excess put. Without the full source, a complete path enumeration cannot be performed.

## Callee Source Requests

I need to see the internals of:
- `[NEED_SOURCE] tproxy_tg4` (lines 70‑end)
- `[NEED_SOURCE] nf_tproxy_handle_time_wait4`

These are essential to verify reference handling, particularly whether `nf_tproxy_handle_time_wait4` consumes the original sk reference and whether the missing code contains an extra put.

## Preliminary Verdict (based on visible code)

VERDICT: FALSE_POSITIVE
CONFIDENCE: LOW
The three visible return paths all appear balanced. However, the warning target line is not shown, so a hidden path or a callee bug cannot be ruled out.

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] nf_tproxy_sk_is_transparent

--- [NEED_SOURCE r2] ---

## Path Table for `tproxy_tg4()`

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L45 | NF_DROP     | NO (before any get) | N/A | ✅ | `hp==NULL` – exit immediately |
| L78 | NF_ACCEPT   | YES | YES (consumed by `assign_sock`) | ✅ | `sk` non‑NULL and transparent → `assign_sock` eats the ref |
| L81 (sk==NULL) | NF_DROP | NO (no reference held) | N/A | ✅ | `sk` is NULL, got nothing to release |
| L81 (sk!=NULL, not transparent) | NF_DROP | **YES** | **NO** | ❌ **LEAK** | At L73 the socket is non‑NULL and non‑transparent; we fall through to L81 without doing `sock_put(sk)`, leaking the reference obtained from `nf_tproxy_get_sock_v4` or `nf_tproxy_handle_time_wait4` |

### Explanation

- `nf_tproxy_get_sock_v4()` (called on L51 and L67) returns a socket with an elevated reference count when non‑NULL.
- `nf_tproxy_handle_time_wait4()` (L63) follows the same contract as its IPv6 counterpart: it **consumes** the reference passed in and returns a socket with an **independent** reference.
- The only place that releases the reference is `nf_tproxy_assign_sock()` (L77), which is invoked only when `sk` is **non‑NULL and transparent** (
```
