# REAL BUG: net/sunrpc/svcauth_unix.c:738 svcauth_unix_set_client()

**Confidence**: HIGH | **Counter**: `$->xpt_auth_cache->h.ref.refcount.refs.counter`

## Reasoning

> *`__ip_map_lookup` does not acquire a reference (standard `__` prefix indicates caller holds locks, no refcount change). The contract only lists `ip_map_cached_get` as a GET operation.

## Full Response

```
The refcount excess put warning at `net/sunrpc/svcauth_unix.c:738` occurs on the success return path when `__ip_map_lookup` provides the `ip_map` instead of `ip_map_cached_get`. The contract shows that only `ip_map_cached_get` acquires a reference; `__ip_map_lookup` is a low‑level helper that does **not** take a reference. Calling `ip_map_cached_put` after a successful `cache_check` on an `ipm` from `__ip_map_lookup` therefore decrements a refcount that was never incremented – a definite excess put.

The following path table enumerates every return point in `svcauth_unix_set_client()`, including the two distinct `ipm` sources for the `cache_check` error and success cases.

| Line | Return Type | IPM Source | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|------------|-----------|-----------|-----------|-------|
| ~686 (goto out) | SVC_OK | – | NO (before get) | N/A | ✅ | early exit, no ip_map ops |
| ~695 (ipm == NULL) | SVC_DENIED | – | NO (both lookups failed) | N/A | ✅ | no ipm to release |
| ~700 (ETIMEDOUT), ip_map_cached_get succeeded | SVC_CLOSE | ip_map_cached_get | YES | NO | ❌ LEAK | missing ip_map_cached_put |
| ~700 (ETIMEDOUT), fallback to __ip_map_lookup | SVC_CLOSE | __ip_map_lookup | NO* | NO | ✅ | no reference to release |
| ~702 (EAGAIN), ip_map_cached_get succeeded | SVC_DROP | ip_map_cached_get | YES | NO | ❌ LEAK | missing put |
| ~702 (EAGAIN), fallback | SVC_DROP | __ip_map_lookup | NO* | NO | ✅ | |
| ~704 (ENOENT), ip_map_cached_get succeeded | SVC_DENIED | ip_map_cached_get | YES | NO | ❌ LEAK | |
| ~704 (ENOENT), fallback | SVC_DENIED | __ip_map_lookup | NO* | NO | ✅ | |
| Case 0 → unix_gid_find -EAGAIN (~714), ip_map_cached_get succeeded | SVC_DROP | ip_map_cached_get | YES | YES (in case 0) | ✅ | |
| Case 0 → unix_gid_find -EAGAIN (~714), fallback | SVC_DROP | __ip_map_lookup | NO* | YES | ❌ **EXCESS PUT** | ip_map_cached_put on non‑ref’d entry |
| Case 0 → unix_gid_find -ESHUTDOWN (~716), ip_map_cached_get succeeded | SVC_CLOSE | ip_map_cached_get | YES | YES | ✅ | |
| Case 0 → unix_gid_find -ESHUTDOWN (~716), fallback | SVC_CLOSE | __ip_map_lookup | NO* | YES | ❌ **EXCESS PUT** | |
| Case 0 → -ENOENT break → out (~738), ip_map_cached_get succeeded | SVC_OK | ip_map_cached_get | YES | YES | ✅ | |
| **Case 0 → -ENOENT break → out (~738), fallback** | **SVC_OK** | **__ip_map_lookup** | **NO*** | **YES** | **❌ EXCESS PUT** | **Warning line – put without get** |
| Case 0 → default → out (~738), ip_map_cached_get succeeded | SVC_OK | ip_map_cached_get | YES | YES | ✅ | |
| Case 0 → default → out (~738), fallback | SVC_OK | __ip_map_lookup | NO* | YES | ❌ **EXCESS PUT** | |

> *`__ip_map_lookup` does not acquire a reference (standard `__` prefix indicates caller holds locks, no refcount change). The contract only lists `ip_map_cached_get` as a GET operation.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
__ip_map_lookup returns a pointer without a reference; calling ip_map_cached_put on it in the case-0 success path
```
