# REAL BUG: fs/nfs/dns_resolve.c:277 nfs_dns_parse()

**Confidence**: HIGH | **Counter**: `item->h.ref.refcount.refs.counter`

## Reasoning

unt bug** is the missing `cache_put` on the error path at L256. After `nfs_dns_lookup()` successfully returns a non‑NULL `item` (refcount elevated), if `nfs_dns_update()` later returns NULL the function yields all the way to `out` without releasing that reference, causing a definite refcount leak.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L231 | error (goto out) | NO (before any get) | N/A | ✅ | buf[buflen-1] != '\n' |
| L235 | error (goto out) | NO | N/A | ✅ | qword_get len <=0 |
| L240 | error (goto out) | NO | N/A | ✅ | second qword_get len <=0 |
| L244 | error (goto out) | NO | N/A | ✅ | get_uint < 0 |
| L246 | error (goto out) | NO | N/A | ✅ | ttl == 0 |
| L250 | error (goto out) | NO (nfs_dns_lookup returned NULL) | N/A | ✅ | conditional get failed, no ref |
| L256 | error (goto out) | **YES** (from nfs_dns_lookup) | **NO** | ❌ **LEAK** | nfs_dns_update failed → ref still held, no put |
| L258‑L277 | success | YES | YES (cache_put) | ✅ | normal cleanup |

**Additional note**: The warning line `fs/nfs/dns_resolve.c:277` corresponds to the `cache_put` on the success path. Smatch’s “excess put” warning may originate from tracking the put on a potentially reassigned `item` pointer, but the **real refcount bug** is the missing `cache_put` on the error path at L256. After `nfs_dns_lookup()` successfully returns a non‑NULL `item` (refcount elevated), if `nfs_dns_update()` later returns NULL the function yields all the way to `out` without releasing that reference, causing a definite refcount leak.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error path at L256 (nfs_dns_update==NULL) returns without putting the reference acquired by nfs_dns_lookup, causing a refcount leak; the “excess put” warning on the success path is a side-effect of pointer tracking but the true bug is the missing put in the error path.
```
