# REAL BUG: fs/nfsd/nfs4idmap.c:270 idtoname_parse()

**Confidence**: HIGH | **Counter**: `res->h.ref.refcount.refs.counter`

## Reasoning

| L266 | cache_put + error=0 | YES | YES | ✅ | Normal success path – `cache_put` correctly releases the ref |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L214 | return -EINVAL | NO (before any get) | N/A | ✅ | Buffer not newline‑terminated |
| L219 | return -ENOMEM | NO (before any get) | N/A | ✅ | kmalloc failed |
| L226 | goto out | NO (before get) | N/A | ✅ | authname parsing failure |
| L231 | goto out | NO (before get) | N/A | ✅ | type parsing failure |
| L237 | goto out | NO (before get) | N/A | ✅ | ID parsing failure |
| L240 | goto out | NO (before get) | N/A | ✅ | Invalid ID digits |
| L245 | goto out | NO (before get) | N/A | ✅ | get_expiry failure |
| L250 | goto out (res == NULL) | NO (conditional get failed) | N/A | ✅ | `idtoname_lookup` returned NULL → no ref taken (conditional GET) |
| L256 | goto out | **YES** (idtoname_lookup succeeded) | **NO** | ❌ LEAK | Name parsing failed after successful lookup; ref from `idtoname_lookup` is never released |
| L264 | goto out | **YES** (idtoname_lookup succeeded) | UNCLEAR | POSSIBLE LEAK | `idtoname_update` returned NULL; if it does **not** already release the original ref on error, this is a leak. The definite leak on L256 is sufficient to classify the overall function as having a real bug. |
| L266 | cache_put + error=0 | YES | YES | ✅ | Normal success path – `cache_put` correctly releases the ref |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
After `idtoname_lookup` succeeds at line 248, two error paths – the Name parsing failure (goto out at L256) and the `idtoname_update` failure (goto out at L264) – return without a matching `cache_put`. At minimum, the L256 path is an unambiguous refcount leak, making the function buggy.
```
