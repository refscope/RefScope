# REAL BUG: drivers/infiniband/core/uverbs_cmd.c:1739 ib_uverbs_query_qp()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

- Consequently, every path that **successfully obtained the reference** (the two rows where `GET=YES`) returns with the ref leaked, because the put is misapplied.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1669 | return ret (uverbs_request fail) | NO | N/A | ✅ | before any get |
| ~L1678 | goto out (kmalloc fail) | NO | N/A | ✅ | before get |
| ~L1685 | goto out (IS_ERR after uobj_get_obj_read) | NO (get failed) | N/A | ✅ | |
| ~L1695 (if ret) goto out | goto out after put (ib_query_qp error) | YES | NO (PUT on wrong object) | ❌ LEAK | `rdma_lookup_put_uobject(&qp->uobject->uevent.uobject, …)` releases a ref on a different uobject than the one acquired by `uobj_get_obj_read` |
| ~L1739 (success path → out) | return through out after uverbs_response | YES | NO (PUT on wrong object) | ❌ LEAK | same put mismatch; put never releases the actual uobject’s kref |

**Path Table Notes:**
- `uobj_get_obj_read()` acquires a reference on the `ib_uobject` (the one returned via `qp->uobject`).  
- The code calls `rdma_lookup_put_uobject(&qp->uobject->uevent.uobject, …)`, which passes a pointer to a member embedded inside the uobject structure, **not** the same `ib_uobject` pointer. The put therefore operates on a different object and does **not** release the reference that was taken.  
- Consequently, every path that **successfully obtained the reference** (the two rows where `GET=YES`) returns with the ref leaked, because the put is misapplied.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`uobj_get_obj_read` acquires a reference on `qp->uobject`, but the `rdma_lookup_put_uobject` call uses `&qp->uobject->uevent.uobject` (an embedded member), leaving the actual object’s refcount undropped — a classic mismatched-put leak.
```
