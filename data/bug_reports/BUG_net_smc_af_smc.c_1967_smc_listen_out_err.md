# REAL BUG: net/smc/af_smc.c:1967 smc_listen_out_err()

**Confidence**: HIGH | **Counter**: `new_smc->sk.sk_refcnt.refs.counter`

## Reasoning

| implicit return at end of function – branch where `sk_state != SMC_INIT` | void return | NO | YES (only from smc_listen_out) | ✅ | Correct single release. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| implicit return at end of function (after smc_listen_out) – branch where `sk_state == SMC_INIT` is true | void return | NO (no get in this function) | YES (sock_put at L1967 + sock_put inside smc_listen_out) | ❌ EXCESS PUT | Double sock_put: explicit at L1967 and again inside smc_listen_out (which already handles the SMC_INIT case with the same “passive closing” comment). |
| implicit return at end of function – branch where `sk_state != SMC_INIT` | void return | NO | YES (only from smc_listen_out) | ✅ | Correct single release. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The explicit `sock_put(&new_smc->sk)` under `sk_state == SMC_INIT` duplicates the identical put inside `smc_listen_out()`, causing an excess put and refcount underflow on that path. The warning line (L1967) correctly flags this duplicate.
```
