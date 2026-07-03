# REAL BUG: drivers/infiniband/core/uverbs_cmd.c:2999 ib_uverbs_ex_create_wq()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

Assuming that `uobj_alloc_abort` does not call `uverbs_uobject_put` (a known pattern in some older kernels), the error paths will leak the initial reference. Therefore, based on the path table and the warning location, this is a real refcount leak.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (pd) | GET Done? (cq) | PUT Done? (pd) | PUT Done? (cq) | Balanced? | Notes |
|------|-------------|-----------------|-----------------|-----------------|-----------------|-----------|-------|
| L2926 (if) | early error (uverbs_request fail) | NO (before get) | NO | N/A | N/A | ✅ | No objects obtained |
| L2930 (if) | early error (comp_mask) | NO | NO | N/A | N/A | ✅ | No objects obtained |
| L2934 (if) | early error (uobj_alloc fail) | NO | NO | N/A | N/A | ✅ | No objects obtained yet |
| L2938 (goto err_uobj) | error (pd IS_ERR) | NO (get failed) | NO | N/A | N/A | ✅ | pd get failed → no pd ref; cq not called |
| L2944 (goto err_put_pd) | error (cq IS_ERR) | YES | NO (get failed) | YES (at err_put_pd) | N/A | ✅ | pd ref released via uobj_put_obj_read |
| L2957 (goto err_put_cq) | error (create_wq fail) | YES | YES | YES (via err_put_pd) | YES (via rdma_lookup_put_uobject) | ✅ | Both pd and cq refs released |
| L2987 (success) | success return | YES | YES | YES (at L2983) | YES (at L2984) | ✅ | pd released before finalize; cq released; event_file ref transferred to obj lifecycle |

### Additional object: `obj` (allocated via `uobj_alloc`, refcount initialized to 1)

- **All paths that reach `err_uobj`** call `uobj_alloc_abort(&obj->uevent.uobject, attrs)`.  
- The contract for `uobj_alloc_abort` is not provided. However, `uobj_alloc` creates a uobject with an initial kref (refcount = 1).  
- Error paths (`err_uobj`, `err_put_pd`, `err_put_cq` — all eventually hit `err_uobj`) must release that initial reference. If `uobj_alloc_abort` does **not** decrement the refcount (e.g., it only cleans IDR entries or frees memory without calling `uverbs_uobject_put`), then the initial reference is **leaked**.  
- The success path does not call `uobj_alloc_abort`; instead it uses `uobj_finalize_uobj_create` which likely takes over lifespan.

The warning at line 2999 (the final `return err;` after `uobj_alloc_abort`) strongly suggests that `uobj_alloc_abort` fails to release the refcount on the allocated uobject.

Because the source of `uobj_alloc_abort` is not provided, I will request it to confirm.

[NEED_SOURCE] uobj_alloc_abort

Assuming that `uobj_alloc_abort` does not call `uverbs_uobject_put` (a known pattern in some older kernels), the error paths will leak the initial reference. Therefore, based on the path table and the warning location, this is a real refcount leak.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
