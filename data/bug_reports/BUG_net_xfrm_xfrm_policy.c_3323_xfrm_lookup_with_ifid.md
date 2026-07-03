# REAL BUG: net/xfrm/xfrm_policy.c:3323 xfrm_lookup_with_ifid()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| ~3305 | ok: return dst (successful bundle) | YES | NO (drop_pols not set, xfrm_pols_put with 0) | ❌ LEAK | Ref leaked on non‑error success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~3190 | goto dropdst (expand error) | YES (if lookup returned non‑NULL) | NO (drop_pols=0 → xfrm_pols_put does nothing) | ❌ LEAK | Ref from xfrm_sk_policy_lookup leaked |
| ~3195 | goto no_transform (num_xfrms≤0) | YES | YES (drop_pols=num_pols, released at ok:) | ✅ | |
| ~3204 | goto nopol (xdst ERR, -EREMOTE) | YES | YES (explicit put at 3201 before goto) | ✅ | |
| ~3205 | goto dropdst (xdst ERR, other) | YES | YES (explicit put at 3201) | ✅ | |
| ~3210 | goto no_transform (xdst==NULL) | YES | YES (drop_pols=num_pols) | ✅ | |
| ~3295 | goto error (route NULL, num_xfrms>0) | YES | NO (drop_pols=0 at dropdst) | ❌ LEAK | Ref leaked |
| ~3305 | ok: return dst (successful bundle) | YES | NO (drop_pols not set, xfrm_pols_put with 0) | ❌ LEAK | Ref leaked on non‑error success path |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`xfrm_sk_policy_lookup` obtains a reference that is not released on the early `goto dropdst` after expand failure, on the `goto error` from the route‑NULL path, and on the successful return path after bundle creation, because `drop_pols` remains 0.
```
