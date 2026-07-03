# REAL BUG: net/nfc/digital_dep.c:1074 digital_tg_send_saved_skb()

**Confidence**: MEDIUM | **Counter**: `ddev->saved_skb->users.refs.counter`

## Reasoning

This is a genuine bug (excess put).

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 1063 | error       | NO (before get) | N/A | ✅ | skb is NULL, immediate return -EINVAL |
| 1071 → 1074 | error (rc != 0) | YES (skb_get at 1066) | YES (kfree_skb at 1071) | ⚠️ Potentially excess PUT if `digital_tg_send_cmd` already released the skb on failure | Smatch warning “excess put” indicates a double release on this path |
| 1074 | success (rc == 0) | YES | NO | ❌ LEAK | Extra reference never released, but warning type is excess put, not leak |

[NEED_SOURCE] digital_tg_send_cmd – its internal skb handling on failure is critical to confirm the double‑put.  

Based on the existing contracts (`skb_get` unconditional, `kfree_skb` unconditional) and the smatch “refcount excess put” warning at the return after the error cleanup, the most likely scenario is:  
- `digital_tg_send_cmd` consumes (releases) the skb even when it returns an error.  
- After that error return, `kfree_skb` in `digital_tg_send_saved_skb` releases the skb again → double put → refcount underflow.  

This is a genuine bug (excess put).  

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM
```
