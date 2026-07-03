# REAL BUG: crypto/api.c:250 crypto_larval_wait()

**Confidence**: HIGH | **Counter**: `$->cra_refcnt.refs.counter`

## Reasoning

erence at line 250. If the adult algorithm remains a larval (`crypto_is_larval` true) the code jumps back to `again` *after* that put. The second pass uses the same `larval` pointer (now stale) and again executes `crypto_mod_put(&larval->alg)`, causing an excess decrement on the larval’s refcount.

## Full Response

```
## Path Table

| Line(s) | Return Type | GET Done? (larval ref) | PUT Done? (larval ref) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L203–L250 executed once, then `crypto_is_larval(alg)` false → `return alg` | success or error | caller's reference (obtained before entry) | single `crypto_mod_put(&larval->alg)` at L250 | ✅ | normal single‑release |
| L203–L250 executed once, then `!IS_ERR(alg) && crypto_is_larval(alg)` true → `goto again` → re‑enter function body (L203) → later again reach L250 and execute `crypto_mod_put(&larval->alg)` → `return alg` | success or error | caller's reference already released by the first L250 | second `crypto_mod_put(&larval->alg)` at L250 | ❌ EXCESS PUT | double‑put on the larval’s `cra_refcnt`; refcount goes negative – ***the path that triggers the warning*** |

The function unconditionally puts the larval’s reference at line 250. If the adult algorithm remains a larval (`crypto_is_larval` true) the code jumps back to `again` *after* that put. The second pass uses the same `larval` pointer (now stale) and again executes `crypto_mod_put(&larval->alg)`, causing an excess decrement on the larval’s refcount.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
