# REAL BUG: net/core/sock_map.c:336 sock_map_link()

**Confidence**: HIGH | **Counter**: `psock->refcnt.refs.counter`

## Reasoning

nt_set`) and holds a `sock_hold` regardless of the return value. Per the audit rules, any `IS_ERR` path after an unconditional GET that does not call the matching PUT is a leak. The `goto out_progs` at L264 after `sk_psock_init` failure performs no `sk_psock_put`, leaving the reference unbalanced.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L228 | early error (stream_verdict fail) | NO (before psock) | N/A | ✅ | |
| L235 | goto out_put_stream_verdict (stream_parser error) | NO | N/A | ✅ | |
| L243 | goto out_put_stream_parser (msg_parser error) | NO | N/A | ✅ | |
| L251 | goto out_put_msg_parser (skb_verdict error) | NO | N/A | ✅ | |
| L256 | IS_ERR(psock) from sock_map_psock_get_checked → goto out_progs | NO (conditional get, error) | N/A | ✅ | contract: conditional, only on success; ERR implies no ref |
| L268 | psock != NULL, conflict → sk_psock_put then goto out_progs | YES (from get_checked) | YES | ✅ | put at L268 |
| L285 | psock != NULL, sock_map_init_proto < 0 → sk_psock_put; goto out | YES | YES | ✅ | put at L285 |
| L304 | psock != NULL, strp/verdict error inside lock → sk_psock_put; goto out | YES | YES | ✅ | put at L304 |
| L315 | psock != NULL, success return 0 | YES | NO (intentional lifetime hold) | ✅ | reference held for map/socket lifetime |
| L264 | psock == NULL, sk_psock_init returns IS_ERR → goto out_progs | ✅ YES (contract: unconditional refcount_set + sock_hold) | ❌ NO | ❌ **LEAK** | sk_psock_init unconditionally acquires a ref; error path does not call sk_psock_put |
| L264‑>success | psock from sk_psock_init success path | YES | on error paths: YES; on final return 0: NO (lifetime) | balanced for all sub‑paths | later error returns call sk_psock_put; success is intentional |

The contract for `sk_psock_init` states it is **unconditional** → it always sets the initial reference (`refcount_set`) and holds a `sock_hold` regardless of the return value. Per the audit rules, any `IS_ERR` path after an unconditional GET that does not call the matching PUT is a leak. The `goto out_progs` at L264 after `sk_psock_init` failure performs no `sk_psock_put`, leaving the reference unbalanced.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`sk_psock_init` unconditionally acquires a psock reference (contract states refcount_set + sock_hold). The error path `IS_ERR(psock) → goto out_progs` (line L264) never calls `sk_psock_put`, leaking the reference.
```
