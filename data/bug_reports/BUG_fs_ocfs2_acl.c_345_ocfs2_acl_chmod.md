# REAL BUG: fs/ocfs2/acl.c:345 ocfs2_acl_chmod()

**Confidence**: HIGH | **Counter**: `$->a_refcount.refs.counter`

## Reasoning

| L345 | success | YES | YES (posix_acl_release at L344) | ✅ | normal path, releases the caller’s reference |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L329 | error (-EOPNOTSUPP) | NO (before get) | N/A  | ✅ | acl not yet obtained |
| L332 | error (0) | NO (before get) | N/A  | ✅ | mount option disables ACL |
| L338 | IS_ERR_OR_NULL guard | NO (get failed/zero) | N/A  | ✅ | acl is ERR_PTR or NULL → no ref held |
| L341 | error (ret from __posix_acl_chmod) | YES (acl ref from ocfs2_get_acl_nolock) | NO  | ❌ LEAK | __posix_acl_chmod fails; on error it does NOT release the old acl, caller must release |
| L345 | success | YES | YES (posix_acl_release at L344) | ✅ | normal path, releases the caller’s reference |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__posix_acl_chmod` does not release the old ACL on error; the early return at L341 leaks the reference acquired from `ocfs2_get_acl_nolock` at L335.
```
