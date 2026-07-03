# REAL BUG: net/xfrm/xfrm_state.c:2276 xfrm_state_update()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L2252 (goto fail, not VALID) | error (-EINVAL) | YES | YES (fail label) | NO (error path) | ✅ | x1 put, x retained by caller |

## Full Response

```
| Line | Return Type | GET (x1) from locate? | PUT (x1) done? | x consumed (__xfrm_state_put)? | Balanced? | Notes |
|------|-------------|-----------------------|----------------|--------------------------------|-----------|-------|
| L2189 (goto out, x1==NULL) | error (-ESRCH)  | NO (NULL) | N/A | NO (error path) | ✅ | No x1 ref, x not consumed |
| L2192 (goto out, x1 kern) | error (-EEXIST) | YES | YES (to_put=x1) | NO (error path) | ✅ | x1 put, x not consumed |
| L2197 (goto out, ACQ dir mismatch) | error (-ESRCH) | YES | YES (to_put=x1) | NO (error path) | ✅ | x1 put, x not consumed |
| L2202 (ACQ + insert, x=NULL, then return 0) | success | YES | YES (inside !x block) | **NO** | ❌ **LEAK** | x inserted into tree, caller’s reference never released |
| L2212 (goto out, non-ACQ dir mismatch) | error (-ESRCH) | YES | YES (to_put=x1) | NO (error path) | ✅ | x1 put, x not consumed |
| L2245 (fail, copy success) | success (0) | YES | YES (fail label) | YES (before fail) | ✅ | Both x1 and x released |
| L2239 (goto fail, encap mismatch) | error (-EINVAL) | YES | YES (fail label) | NO (error path) | ✅ | x1 put, x retained by caller |
| L2252 (goto fail, not VALID) | error (-EINVAL) | YES | YES (fail label) | NO (error path) | ✅ | x1 put, x retained by caller |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the ACQ success path, `__xfrm_state_insert(x)` transfers ownership of x to the tree, but the caller’s original reference on x is never released, while the non-ACQ success path correctly calls `__xfrm_state_put(x)`. This leaks a reference on x.
```
