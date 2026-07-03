# REAL BUG: net/bluetooth/mgmt.c:1988 set_ssp_complete()

**Confidence**: HIGH | **Counter**: `$->sk->sk_refcnt.refs.counter`

## Reasoning

| L1988 (success, settings_rsp **did NOT** sock_hold, match.sk≠NULL) | end | NO | YES (sock_put) | YES | ❌ EXCESS PUT | sock_put at L1985 drops ref not owned; mgmt_pending_free at L1988 sees zero ref → refcount underflow |

## Full Response

```
| Line | Return Type | GET Done? (settings_rsp sock_hold) | PUT Done? (sock_put match.sk) | PUT Done? (mgmt_pending_free cmd->sk) | Balanced? | Notes |
|------|-------------|-----------------------------------|-------------------------------|---------------------------------------|-----------|-------|
| L1954-L1955 (err==-ECANCELED or !valid) | early return | NO (settings_rsp not called) | NO | NO | ✅ | cmd not processed, no ref touched |
| L1970 (err != 0) | error return | NO (settings_rsp not called) | NO | YES (via mgmt_pending_free) | ✅ | pending reference released |
| L1988 (success, settings_rsp **did** sock_hold, match.sk≠NULL) | end | YES | YES | YES | ✅ | extra ref from response put, pending ref freed |
| L1988 (success, settings_rsp **did NOT** sock_hold, match.sk≠NULL) | end | NO | YES (sock_put) | YES | ❌ EXCESS PUT | sock_put at L1985 drops ref not owned; mgmt_pending_free at L1988 sees zero ref → refcount underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
settings_rsp() conditionally holds a reference on match.sk (contract: conditional_on_path) but the caller unconditionally does sock_put(match.sk) at L1985 if match.sk is non‑NULL. When settings_rsp sets match.sk without holding a reference, the extra sock_put combined with mgmt_pending_free at L1988 causes a double‑put, triggering the excess put warning.
```
