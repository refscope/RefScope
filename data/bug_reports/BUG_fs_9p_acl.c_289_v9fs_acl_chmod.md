# REAL BUG: fs/9p/acl.c:289 v9fs_acl_chmod()

**Confidence**: HIGH | **Counter**: `$->a_refcount.refs.counter`

## Reasoning

| L289 | error/success (after release) | YES | YES (L287) | ✅ | acl released in all paths after set |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L279 | error (-EOPNOTSUPP) | NO (before get) | N/A | ✅ | get hasn't happened |
| L289 | success (acl == NULL) | NO (get returned NULL) | N/A | ✅ | conditional get, no ref held |
| L284 | error (__posix_acl_chmod failure) | YES (acl non-NULL) | NO | ❌ LEAK | error return without releasing acl |
| L289 | error/success (after release) | YES | YES (L287) | ✅ | acl released in all paths after set |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__posix_acl_chmod` failure at L282 skips `posix_acl_release(acl)` at L287, leaking the reference acquired by `v9fs_get_cached_acl` at L280.
```
