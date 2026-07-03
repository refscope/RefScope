# REAL BUG: net/key/af_key.c:1547 pfkey_add()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

- `__xfrm_state_put` is an unconditional put (contract), so the hold reference is released twice. The refcount drops to 0 with the first put, and the second put at line 1547 triggers an excess put warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1519 | error (IS_ERR) | NO (before get) | N/A  | ✅ | xfrm_state_hold not yet called |
| L1533 → out (L1547) | error (err < 0) | YES (xfrm_state_hold at L1521) | YES (two puts: __xfrm_state_put at L1532, then xfrm_state_put at L1547) | ❌ EXCESS | Double put on error path; second put (xfrm_state_put) is excess when refcount already 0 |
| L1547 (out, success) | success (err ≥ 0) | YES (xfrm_state_hold at L1521) | YES (xfrm_state_put at L1547) | ✅ | Single put matches the hold |

**Reasoning**: 
- `xfrm_state_hold(x)` unconditionally increments the refcount (confirmed by contract).  
- On the error path (`err < 0`), `__xfrm_state_put(x)` is called, then execution falls through to `out:` where `xfrm_state_put(x)` is called again.  
- `__xfrm_state_put` is an unconditional put (contract), so the hold reference is released twice. The refcount drops to 0 with the first put, and the second put at line 1547 triggers an excess put warning.  

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
