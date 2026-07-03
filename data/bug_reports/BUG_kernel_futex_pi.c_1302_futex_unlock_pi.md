# REAL BUG: kernel/futex/pi.c:1302 futex_unlock_pi()

**Confidence**: HIGH | **Counter**: `pi_state->refcount.refs.counter`

## Reasoning

- In that path, the pi_state pointer is obtained from `top_waiter->pi_state`, and the waiter originally held a reference. No `put_pi_state()` is called, leaving the pi_state refcount permanently elevated.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1150 | error (return -ENOSYS) | NO (no pi_state) | N/A | ✅ | |
| L1157 | error (return -EFAULT) | NO | N/A | ✅ | |
| L1161 | error (return -EPERM) | NO | N/A | ✅ | |
| L1165 | error (return from get_futex_key) | NO | N/A | ✅ | |
| L1183 (goto out_unlock) | error (!pi_state) | NO | N/A | ✅ | |
| L1189 (goto out_unlock) | error (pi_state->owner != current) | NO | N/A | ✅ | |
| L1211 (goto retry_hb) | error (rt_waiter NULL) | YES (waiter holds pi_state ref) | NO | ❌ LEAK | __futex_unqueue drops the waiter but does not call put_pi_state |
| L1220‑1221 → ret==0 | success (return 0) | YES (get_pi_state + put_pi_state) | YES | ✅ | |
| L1229 (goto pi_faulted) | retry after -EFAULT | YES (get + put already done) | YES | ✅ | |
| L1233 (goto pi_retry) | retry after -EAGAIN | YES | YES | ✅ | |
| L1238 (return ret) | error (wake_futex_pi invalid) | YES | YES | ✅ | |
| L1247‑1257 (switch paths) | error (cmpxchg failure, etc.) | NO | N/A | ✅ | |
| L1263 (out_unlock return) | error (out_unlock label) | NO | N/A | ✅ | |
| L1267 (goto retry from pi_retry) | retry | NO | N/A | ✅ | |
| L1273 (return ret from pi_faulted) | error (fault_in_user_writeable fail) | NO | N/A | ✅ | |

- The **⬤ LEAK** row corresponds to the `if (!rt_waiter)` block, where the waiter’s pi_state reference is never released after unqueue.
- In that path, the pi_state pointer is obtained from `top_waiter->pi_state`, and the waiter originally held a reference. No `put_pi_state()` is called, leaving the pi_state refcount permanently elevated.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

futex_unlock_pi() unqueues a futex waiter when rt_waiter is NULL but never calls put_pi_state() to release the pi_state reference held by that waiter, causing a permanent refcount leak on pi_state.
```
