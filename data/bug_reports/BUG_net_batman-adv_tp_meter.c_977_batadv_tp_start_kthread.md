# REAL BUG: net/batman-adv/tp_meter.c:977 batadv_tp_start_kthread()

**Confidence**: HIGH | **Counter**: `tp_vars->refcount.refcount.refs.counter`

## Reasoning

| L977 (implicit) | success | YES (kref_get) | NO | ✅ (deferred) | Reference transferred to kthread; kthread will later call batadv_tp_vars_put. No leak in function scope. |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L974 | error (IS_ERR) | YES (kref_get at L958) | YES (batadv_tp_vars_put at L969, batadv_tp_sender_cleanup at L972 also contains a PUT) | ❌ EXCESS PUT | Two puts for one get: kref_get → refcount++, batadv_tp_vars_put → refcount-- (drops reserved ref), batadv_tp_sender_cleanup → batadv_tp_vars_put → refcount-- (extra drop). Net refcount underflow on this path. |
| L977 (implicit) | success | YES (kref_get) | NO | ✅ (deferred) | Reference transferred to kthread; kthread will later call batadv_tp_vars_put. No leak in function scope. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In error path, kref_get acquires one reference; batadv_tp_vars_put drops it, but batadv_tp_sender_cleanup unconditionally calls batadv_tp_vars_put again, leading to a double put and refcount underflow.
```
```
