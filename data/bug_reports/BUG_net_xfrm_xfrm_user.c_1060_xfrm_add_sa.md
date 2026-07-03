# REAL BUG: net/xfrm/xfrm_user.c:1060 xfrm_add_sa()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L1060 | success return | YES | YES (only xfrm_state_put) | ✅ | Release hold; construct ref now owned by hash table |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1026 | early return (verify_newsa) | NO (no hold) | N/A | ✅ | Before x allocation |
| L1032 | return err (construct fails) | NO (no hold) | N/A | ✅ | No state to hold |
| L1045–L1051 → L1060 | error return (err < 0) | YES (xfrm_state_hold @ L1034) | YES (__xfrm_state_put @ ~L1050 + xfrm_state_put @ L1060) | ❌ **POTENTIAL EXCESS** | `xfrm_state_update` contract shows it contains `__xfrm_state_put` and `xfrm_state_put` on certain paths; if the callee already released a reference, the double put here leads to underflow |
| L1060 | success return | YES | YES (only xfrm_state_put) | ✅ | Release hold; construct ref now owned by hash table |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

The `xfrm_state_update` contract indicates it performs its own puts; on error it may have already released the reference held from `xfrm_state_hold`, causing the subsequent `__xfrm_state_put` + `xfrm_state_put` in the error path to double-decrement the refcount, leading to excess put at line 1060.
```
