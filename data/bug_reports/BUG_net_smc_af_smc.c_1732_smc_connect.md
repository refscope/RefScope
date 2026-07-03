# REAL BUG: net/smc/af_smc.c:1732 smc_connect()

**Confidence**: MEDIUM | **Counter**: `smc->sk.sk_refcnt.refs.counter`

## Reasoning

- `smc_connect_work()` (the work handler) — does it call a put on completion/failure?

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1665 | goto out_err | NO | N/A | ✅ | alen check, before any get |
| L1669 | goto out_err | NO | N/A | ✅ | sa_family check |
| L1673 | goto out | NO | N/A | ✅ | default sock->state |
| L1676 | goto out | NO | N/A | ✅ | SS_CONNECTED case |
| L1679 | goto connected | NO | N/A | ✅ | SS_CONNECTING + SMC_ACTIVE, jumps past sock_hold |
| L1685 | goto out | NO | N/A | ✅ | default sk_state |
| L1688 | goto out | NO | N/A | ✅ | SMC_CLOSED case |
| L1691 | goto out | NO | N/A | ✅ | SMC_ACTIVE case |
| L1697 | goto out | NO | N/A | ✅ | connect_nonblock already set, rc=-EALREADY |
| L1701 | goto out | NO | N/A | ✅ | kernel_connect error (not EINPROGRESS) |
| L1704 | goto out | NO | N/A | ✅ | use_fallback true |
| L1709‑1712 (non‑block, queue_work success) | goto out | **YES** (unconditional sock_hold) | **NO** (no explicit put; work may later put – uncertain) | ❓ | sock_hold executed; deferred to `connect_work` — if that work never runs/doesn’t put, leak. |
| L1709‑1712 (non‑block, queue_work failure) | goto out | **YES** | **NO** (work not scheduled) | ❌ **LEAK** | No deferred cleanup, ref held forever. |
| L1715 (blocking, __smc_connect error) | goto out | **YES** | **NO** (no put in this path; unknown if __smc_connect puts on error) | ❌ **LEAK** (unless __smc_connect puts) | sock_hold executed; __smc_connect returned <0, goto out skips any put. |
| L1719 (blocking, success) | fall‑through → connected → out | **YES** | **NO** (no explicit put here; unknown if __smc_connect consumed the ref) | ❌ **LEAK** (unless __smc_connect or passive‑close logic absorbs it) | Same hold, no release on success path either. |

**Notes on ownership transfer / passive closing:**
- Comment `/* sock put in passive closing */` indicates the extra ref is meant to be released during a passive close event, not in this function.
- This deferred release only applies if the socket actually enters a state where passive closing occurs. If `__smc_connect` fails or the non‑blocking work is never scheduled, the socket may be torn down without that event ever firing → the reference is leaked.
- Similarly, even the **success** path does not exhibit an immediate put; if `__smc_connect` does not consume the reference, the same leak exists on the success return.

**Missing source needed for definitive analysis:**
- `__smc_connect()` — does it decrement the extra reference on error, or on success transform ownership so that `sock_put` will happen later?
- `smc_connect_work()` (the work handler) — does it call a put on completion/failure?

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
Multiple paths after an unconditional `sock_hold()` reach `goto out` without a matching `sock_put()`. The absence of cleanup on the `queue_work` failure path is a clear leak; the other paths depend on callees that are not provided, but the comment “sock put in passive closing” strongly sugge
```
