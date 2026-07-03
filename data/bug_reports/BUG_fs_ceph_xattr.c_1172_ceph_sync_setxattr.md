# REAL BUG: fs/ceph/xattr.c:1172 ceph_sync_setxattr()

**Confidence**: HIGH | **Counter**: `$->r_kref.refcount.refs.counter`

## Reasoning

| L1172 | success/error (via out) | YES | YES (line 1172) | ❌ EXCESS PUT | ceph_mdsc_do_request already consumed the request ref, this put is extra |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1118 | early error   | NO (before req) | N/A  | ✅ | pagelist alloc failure |
| L1123 | goto out       | NO (before req) | N/A  | ✅ | pagelist append error |
| L1133 | goto out       | NO (req IS_ERR) | N/A  | ✅ | create_request returned error |
| L1141 | goto out       | YES | YES (explicit) | ✅ | r_path2 allocation failed, put before goto |
| L1172 | success/error (via out) | YES | YES (line 1172) | ❌ EXCESS PUT | ceph_mdsc_do_request already consumed the request ref, this put is extra |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
ceph_mdsc_do_request internally drops the request reference, making the ceph_mdsc_put_request at line 1172 an excess put and potential use-after-free.
```
