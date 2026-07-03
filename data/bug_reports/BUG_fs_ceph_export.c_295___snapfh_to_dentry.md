# REAL BUG: fs/ceph/export.c:295 __snapfh_to_dentry()

**Confidence**: HIGH | **Counter**: `$->r_kref.refcount.refs.counter`

## Reasoning

| L286/L295 | success or error | YES (get succeeded) | YES (ceph_mdsc_put_request at L286) | ❌ EXCESS PUT | Reference already consumed by ceph_mdsc_do_request(); the put at L286 operates on a zero refcount, causing underflow |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L238 | error (-ESTALE) | NO (before get) | N/A | ✅ | reserved vino early return |
| L244 | error (-ESTALE) | NO (before get) | N/A | ✅ | inode shutdown, iput(inode) |
| L246 | success (dentry) | NO (before get) | N/A | ✅ | found inode, d_obtain_alias |
| L252 | error (ERR_PTR) | NO (get failed) | N/A | ✅ | ceph_mdsc_create_request returned error, no valid req |
| L286/L295 | success or error | YES (get succeeded) | YES (ceph_mdsc_put_request at L286) | ❌ EXCESS PUT | Reference already consumed by ceph_mdsc_do_request(); the put at L286 operates on a zero refcount, causing underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
ceph_mdsc_do_request() consumes the request's reference, yet the caller drops it again via ceph_mdsc_put_request at line 286, leading to a kref underflow (excess put). The function should not release the request after a successful do_request call.
```
