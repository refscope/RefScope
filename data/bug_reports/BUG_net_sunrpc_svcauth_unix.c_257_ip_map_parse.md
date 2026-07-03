# REAL BUG: net/sunrpc/svcauth_unix.c:257 ip_map_parse()

**Confidence**: MEDIUM | **Counter**: `dom->ref.refcount.refs.counter`

## Reasoning

d. The static analysis pinpoints L257 as the excess, strongly suggesting `__ip_map_update` consumed the ref without incrementing. Without the source of `__ip_map_update` we cannot confirm the exact ownership, but the pattern and warning make a double-put very likely.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L184 | -EINVAL     | NO (before get) | N/A  | ✅ | mesg newline check |
| L188 | -EINVAL     | NO (before get) | N/A  | ✅ | class length ≤ 0 |
| L192 | -EINVAL     | NO (before get) | N/A  | ✅ | ip address length ≤ 0 |
| L194 | -EINVAL     | NO (before get) | N/A  | ✅ | rpc_pton failure |
| L204 | -EINVAL     | NO (before get) | N/A  | ✅ | default address family |
| L210 | err         | NO (before get) | N/A  | ✅ | get_expiry error |
| L215 | -EINVAL     | NO (before get) | N/A  | ✅ | domain length < 0 |
| L218-220 | -ENOENT | NO (dom==NULL) | N/A  | ✅ | unix_domain_find failed |
| L257 (dom != NULL, ipmp != NULL) | return err via __ip_map_update | YES (unix_domain_find) | YES (auth_domain_put at L257) | Potentially ❌ | Warning: excess put at L257. If __ip_map_update already releases the ref, this is a double-put. |
| L257 (dom != NULL, ipmp == NULL) | return -ENOMEM | YES (unix_domain_find) | YES (auth_domain_put at L257) | ✅ if no prior put; else ❌ | Same put, balanced unless __ip_map_update had no involvement. |
| L257 (dom == NULL) | return err | NO | N/A  | ✅ | dom NULL, put skipped |

**Critical cross‑function unknown:** `__ip_map_update` can internally take or release the reference on `dom`. The `auth_domain_put(dom)` at L257 is called unconditionally after the update, so if the update already dropped the reference (e.g., to transfer ownership), the L257 put triggers an underflow → `refcount excess put` exactly as warned. The static analysis pinpoints L257 as the excess, strongly suggesting `__ip_map_update` consumed the ref without incrementing. Without the source of `__ip_map_update` we cannot confirm the exact ownership, but the pattern and warning make a double-put very likely.

[NEED_SOURCE] __ip_map_update

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM (depends on confirmation that __ip_map_update releases the reference without acquiring its own, making the caller’s put at L257 a redundant underflow.)
```
