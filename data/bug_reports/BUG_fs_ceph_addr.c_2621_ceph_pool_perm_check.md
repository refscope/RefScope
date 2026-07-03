# REAL BUG: fs/ceph/addr.c:2621 ceph_pool_perm_check()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| ~2588/2592 (after goto check) | success path: -EPERM from check | YES | NO | ❌ LEAK | same |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~2562 | early return (not regular file) | NO | N/A | ✅ | before any get |
| ~2569 | early return (snapshot) | NO | N/A | ✅ | before get |
| ~2578 | early return (NOPOOLPERM) | NO | N/A | ✅ | before get |
| ~2588 | check label: -EPERM (no RD) | NO (flag already set) | N/A | ✅ | does not call __ceph_pool_perm_get |
| ~2592 | check label: -EPERM (no WR) | NO | N/A | ✅ | same |
| ~2595 | check label: return 0 (permitted) | NO | N/A | ✅ | same |
| 2621 | error return (ret < 0) | YES (unconditional get from __ceph_pool_perm_get) | NO (only single ceph_put_string for try_get) | ❌ LEAK | extra ref on pool_ns not released |
| ~2595 (after goto check) | success path: return 0 from check | YES (same get) | NO (no put for the extra get) | ❌ LEAK | same |
| ~2588/2592 (after goto check) | success path: -EPERM from check | YES | NO | ❌ LEAK | same |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
__ceph_pool_perm_get unconditionally increments pool_ns via ceph_get_string, but the caller only releases the original ceph_try_get_string reference, leaking one refon the error path and on every subsequent success path.
```
