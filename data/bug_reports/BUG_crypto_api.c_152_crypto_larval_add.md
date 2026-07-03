# REAL BUG: crypto/api.c:152 crypto_larval_add()

**Confidence**: HIGH | **Counter**: `$->cra_refcnt.refs.counter`

## Reasoning

| L144–L152 | success (returning `alg`, not larval) | NO get on larval; `refcount_set` already set to 2 | NO `crypto_mod_put` before `kfree(larval)` | ❌ LEAK | `kfree(larval)` at L146 without releasing the 2 references; any get on `alg` inside `crypto_larval_wait` is unrelated |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L130 | error       | NO (before any get)        | N/A  | ✅        | allocation failed, `larval` never initialized |
| L140 | success (returning larval) | NO get on larval; `refcount_set` inits to 2 | Not needed here: caller and list will later release via `crypto_mod_put` | ✅ | larval added to list, both refs accounted for |
| L144–L152 | success (returning `alg`, not larval) | NO get on larval; `refcount_set` already set to 2 | NO `crypto_mod_put` before `kfree(larval)` | ❌ LEAK | `kfree(larval)` at L146 without releasing the 2 references; any get on `alg` inside `crypto_larval_wait` is unrelated |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`refcount_set` sets `larval->alg.cra_refcnt` to 2; when the lookup succeeds and the larval is not used, the code `kfree(larval)` without a matching `crypto_mod_put` leaves a non-zero refcount and misses required cleanup.
```
