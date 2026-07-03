# REAL BUG: net/bluetooth/rfcomm/sock.c:987 rfcomm_connect_ind()

**Confidence**: HIGH | **Counter**: `sk->sk_peer_pid->count.refs.counter`

## Reasoning

No ownership transfer, no deferred cleanup, no IS_ERR guards apply because the put is inside the callee.

## Full Response

```
## Path Table for `rfcomm_connect_ind()` (net/bluetooth/rfcomm/sock.c)

| Line | Return Type | GET Done? (on `sk_peer_pid`) | PUT Done? | Balanced? | Notes |
|------|-------------|-------------------------------|-----------|-----------|-------|
| L955 | early return `0` | NO (before any pid ref) | N/A | ✅ | `parent` NULL, function returns immediately |
| L965 | `goto done` (backlog full) | NO | NO via this path | ✅ | No `bt_accept_enqueue` called |
| L970 | `goto done` (alloc fails) | NO | NO via this path | ✅ | No `bt_accept_enqueue` called |
| L987 | `bt_accept_enqueue()` call, then `result = 1`, final return | **N/A** (put is inside `bt_accept_enqueue` on `parent->sk_peer_pid`) | **YES** (unconditional `put_pid` defined by contract) | ❌ **EXCESS PUT** | The called function unconditionally decrements `sk_peer_pid` refcount, causing excess put if the parent’s pid ref is not properly held. Warning line exactly matches this call. |

**Rationale:**
- `bt_accept_enqueue(parent, sk, true)` is the **only** location where a refcount operation on `sk_peer_pid` occurs in this code.
- According to the contract, `bt_accept_enqueue` **unconditionally** performs `put_pid(put)` (along with `put_cred` and `sock_hold`).
- The warning says an *excess put* on `sk_peer_pid` happens **at line 987**, which is exactly this call. This means the parent socket’s pid reference counter was not properly acquired or was already too low when `bt_accept_enqueue` tried to release it, resulting in an underflow (put without matching get).
- The function `rfcomm_connect_ind` does **not** itself acquire any `sk_peer_pid` reference; the imbalance is therefore either inside `bt_accept_enqueue` (if it should conditionally put) or due to a missing `get` elsewhere. Contract says it’s unconditional → the put is always executed → **excess put is a real bug** triggered by this code path.

No ownership transfer, no deferred cleanup, no IS_ERR guards apply because the put is inside the callee.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
The unconditional `put_pid` inside `bt_accept_enqueue()` (as documented by the contracts) causes an excess put on the parent socket’s `sk_peer_pid` at line 987, leading to an underflow. The caller provides no prior `get` on this refcount, making the put unbalanced.
```
