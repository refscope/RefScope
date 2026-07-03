# REAL BUG: fs/ceph/mds_client.c:4177 handle_forward()

**Confidence**: HIGH | **Counter**: `$->r_kref.refcount.refs.counter`

## Reasoning

| L4144–4150 (resend) then L4152 put | regular exit | YES | Unknown (depends on `__do_request`) | Need source | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| decode error (bad: L4164) | error | NO (before `lookup_get_request`) | NO | ✅ | Jump from `ceph_decode_need` before mutex, no request. |
| L4124 `req == NULL` return | early return | NO (lookup failed) | NO | ✅ | `lookup_get_request` returned NULL, no reference taken. |
| L4127–4131 (ABORTED, `__unregister_request`) then L4152 `ceph_mdsc_put_request` | regular exit | YES (from `lookup_get_request`) | YES (`__unregister_request` already put + final put) | ❌ **EXCESS PUT** | `__unregister_request` unconditionally calls `ceph_mdsc_put_request`, then final put does a second decrement → refcount goes negative. |
| L4133–4142 (overflow, `aborted = true`) then L4148 `complete_request`, L4152 put | regular exit | YES | Unknown (depends on `complete_request`) | Need source | |
| L4144–4150 (resend) then L4152 put | regular exit | YES | Unknown (depends on `__do_request`) | Need source | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__unregister_request` already releases the reference from `lookup_get_request`, but the function unconditionally calls `ceph_mdsc_put_request` on the same request afterward, causing an excess put and use-after-free.
```
