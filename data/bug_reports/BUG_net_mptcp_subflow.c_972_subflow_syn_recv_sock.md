# REAL BUG: net/mptcp/subflow.c:972 subflow_syn_recv_sock()

**Confidence**: HIGH | **Counter**: `$->sk_refcnt.refs.counter`

## Reasoning

| L947 (return child, main success) | success | YES (mp_capable/clone_init success or mp_join/finish_join true) | NO | ✅ | gets are released elsewhere |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L866 (goto dispose_child+return L958) | error (fallback_is_fatal) | NO (before any get) | YES (tcp_done at L953) | ❌ EXCESS | tcp_done without prior mptcp_finish_join or mptcp_sk_clone_init get |
| L898 (goto dispose_child+return L958) | error (!owner) | NO | YES | ❌ EXCESS | same |
| L904 (goto dispose_child+return L958) | error (!hmac_valid) | NO | YES | ❌ EXCESS | same |
| L910 (goto dispose_child+return L958) | error (!accept_new) | NO | YES | ❌ EXCESS | same |
| L924 (goto dispose_child+return L958) | error (!sport_in_list) | NO | YES | ❌ EXCESS | same |
| L933 (goto dispose_child+return L958) | error (mptcp_finish_join failed) | YES (mptcp_finish_join unconditional) | YES | ✅ | get from mptcp_finish_join compensates the put |
| L868 (goto fallback+return L964) | error (fallback) | NO | NO | ✅ | no get, no put |
| L877 (goto fallback+return L964) | error (clone_init failed) | NO (conditional get not taken) | NO | ✅ | no get |
| L947 (return child, main success) | success | YES (mp_capable/clone_init success or mp_join/finish_join true) | NO | ✅ | gets are released elsewhere |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

Early error paths in `subflow_syn_recv_sock()` (fallback_is_fatal, !owner, hmac/accept/sport checks) jump to `dispose_child` before any unconditional `sock_hold` from `mptcp_finish_join` (or conditional `mptcp_sk_clone_init`). The `tcp_done(child)` call at L953 then performs a put on `sk_refcnt` without a matching get, triggering an excess-put warning. Only the path where `mptcp_finish_join` itself fails correctly balances the get.
```
