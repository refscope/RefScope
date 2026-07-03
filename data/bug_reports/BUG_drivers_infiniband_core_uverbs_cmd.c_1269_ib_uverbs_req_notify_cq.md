# REAL BUG: drivers/infiniband/core/uverbs_cmd.c:1269 ib_uverbs_req_notify_cq()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

all) | success return 0 | NO (uevent.uobject was never referenced) | YES (unconditional put on a different uobject) | ❌ EXCESS PUT | The CQ’s own uobject was gotten via `uobj_get_obj_read`, but the put targets `&cq->uobject->uevent.uobject` — a separate refcounted object that was never acquired. |

## Full Response

```
| Line | Return Type | GET Done? (on uevent.uobject) | PUT Done? (on uevent.uobject) | Balanced? | Notes |
|------|-------------|-------------------------------|-------------------------------|-----------|-------|
| L1255 (approx) | error from uverbs_request | NO (before any get) | N/A | ✅ | |
| L1258 (approx) | error from IS_ERR(cq) | NO (lookup failed, no ref on any uobject) | N/A | ✅ | |
| L1269 (the `rdma_lookup_put_uobject` call) | success return 0 | NO (uevent.uobject was never referenced) | YES (unconditional put on a different uobject) | ❌ EXCESS PUT | The CQ’s own uobject was gotten via `uobj_get_obj_read`, but the put targets `&cq->uobject->uevent.uobject` — a separate refcounted object that was never acquired. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ib_uverbs_req_notify_cq` acquires a reference to the CQ uobject via `uobj_get_obj_read`, but then incorrectly calls `rdma_lookup_put_uobject` on `cq->uobject->uevent.uobject`—a completely different uobject that was never referenced, causing an excess refcount underflow.
```
