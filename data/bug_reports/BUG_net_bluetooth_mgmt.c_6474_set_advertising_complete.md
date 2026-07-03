# REAL BUG: net/bluetooth/mgmt.c:6474 set_advertising_complete()

**Confidence**: HIGH | **Counter**: `$->sk->sk_refcnt.refs.counter`

## Reasoning

| L6474‑end | implicit return after enable_advertising_instance | CONDITIONAL | YES (same as above) | ❌ if GET skipped | Same as above. |

## Full Response

```
| Line | Return Type | GET (settings_rsp hold) Done? | PUT (sock_put(match.sk)) Done? | Balanced? | Notes |
|------|-------------|------------------------------|-------------------------------|-----------|-------|
| L6433-6434 | early return (ECANCELED/invalid) | NO (settings_rsp not called) | NO (match.sk NULL) | ✅ | No refs from settings_rsp acquired. |
| L6438-6439 | error return (status != 0) | NO (settings_rsp not called) | NO (match.sk NULL) | ✅ | mgmt_pending_free does balanced put of cmd->sk’s pending ref. |
| L6458-6460 | normal return after advertising flag/list check | CONDITIONAL – may or may not hold | YES (if match.sk non‑NULL) | ❌ if GET skipped | settings_rsp conditionally holds match.sk; the caller unconditionally puts it. On paths where hold did not occur, the put is excessive → refcount underflow. |
| L6466-6467 | return when adv_instance not found | CONDITIONAL | YES (same as above) | ❌ if GET skipped | Same as above. |
| L6474‑end | implicit return after enable_advertising_instance | CONDITIONAL | YES (same as above) | ❌ if GET skipped | Same as above. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The contract states `settings_rsp` conditionally performs `sock_hold` on the socket stored in `match.sk`. The caller later unconditionally calls `sock_put(match.sk)` if `match.sk` is not NULL. On any execution where `settings_rsp` sets `match.sk` but does **not** take the reference, the subsequent `sock_put` releases a reference that it does not own, causing the observed `refcount excess put`. The unconditional put after a conditional get is a classic refcounting imbalance.
```
