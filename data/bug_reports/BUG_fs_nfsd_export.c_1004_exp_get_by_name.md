# REAL BUG: fs/nfsd/export.c:1004 exp_get_by_name()

**Confidence**: HIGH | **Counter**: `exp->h.ref.refcount.refs.counter`

## Reasoning

| L~1004 (`return exp`) | success (returns `exp`) | YES (`svc_export_lookup` succeeded) | YES (`cache_check` unconditional put) | ❌ | `cache_check` released the reference; returning `exp` now has refcount 0 → caller holding no reference will later `cache_put` → **excess put** |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L~989 (`if (!clp) return ERR_PTR(-ENOENT)`) | error (ERR_PTR) | NO (before get) | N/A | ✅ | |
| L~997 (`if (exp == NULL) return ERR_PTR(-ENOMEM)`) | error (ERR_PTR) | NO (lookup failed, no ref) | N/A | ✅ | |
| L~1001 (`if (err) { ... return ERR_PTR(err); }`) | error (ERR_PTR) | YES (`svc_export_lookup` succeeded) | YES (`cache_check` does unconditional put per contract) | ✅ | Ref acquired then released; no leak on error path |
| L~1004 (`return exp`) | success (returns `exp`) | YES (`svc_export_lookup` succeeded) | YES (`cache_check` unconditional put) | ❌ | `cache_check` released the reference; returning `exp` now has refcount 0 → caller holding no reference will later `cache_put` → **excess put** |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After `svc_export_lookup` (unconditional GET) succeeds, `cache_check` (unconditional PUT per contract) releases the reference. The success path returns `exp` without an active reference, causing a future excess put when the caller releases it.
```
