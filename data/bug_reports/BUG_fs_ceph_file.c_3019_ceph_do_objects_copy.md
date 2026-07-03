# REAL BUG: fs/ceph/file.c:3019 ceph_do_objects_copy()

**Confidence**: LOW | **Counter**: `$->r_kref.refcount.refs.counter`

## Reasoning

| req valid, success path → L3019 put, loop continues, exit to out L3028 | success | YES | YES (L3019 put) | ❌ EXCESS PUT | Same double‑put scenario; request already released. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| IS_ERR(req) → ret set, goto out (approx L3028) | error | NO (alloc failed, no start_request) | NO | ✅ | No reference held. |
| req valid, start_request, wait_request returns error → L3019 ceph_osdc_put_request(req) → goto out L3028 | error | YES (ceph_osdc_start_request typically increments refcount) | YES (L3019 put, but smatch sees refcount=0 before put) | ❌ EXCESS PUT | L3019 put is extra: wait_request or completion callback likely already released the request, leaving kref at 0. |
| req valid, success path → L3019 put, loop continues, exit to out L3028 | success | YES | YES (L3019 put) | ❌ EXCESS PUT | Same double‑put scenario; request already released. |

[NEED_SOURCE] ceph_osdc_wait_request  
[NEED_SOURCE] ceph_osdc_start_request  

VERDICT: REAL_BUG  
CONFIDENCE: LOW  

Analysis: The pattern in the Ceph OSD client often has the completion callback (invoked after the request completes) call ceph_osdc_put_request.  After ceph_osdc_wait_request returns, the request’s kref is already 0.  The explicit ceph_osdc_put_request at L3019 therefore triggers an **excess put** (double free / use‑after‑free).  Requesting source for `ceph_osdc_wait_request` to confirm the internal release.
```
