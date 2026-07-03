# REAL BUG: drivers/accel/amdxdna/aie2_ctx.c:741 aie2_hwctx_init()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L718 | success return 0 | YES | NO (ownership retained) | ✅ | heap reference stays with hwctx for later put in fini |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L621 | error (return -ENOMEM) | NO (before get) | N/A | ✅ | priv alloc failed, no heap reference |
| L630 | goto free_priv | NO (before get) | N/A | ✅ | heap is NULL, no get |
| L640 | goto put_heap (pin fail) | YES | YES (single put) | ✅ | explicit put via put_heap |
| L655 | goto free_cmd_bufs (cmd buf alloc fail) | YES | YES (fallthrough) | ✅ | free_cmd_bufs → put_heap |
| L673 | goto free_cmd_bufs (sched init fail) | YES | YES (fallthrough) | ✅ | same chain |
| L680 | goto free_sched (entity init fail) | YES | YES (fallthrough) | ✅ | free_sched → free_cmd_bufs → put_heap |
| L686 | goto free_entity (col list fail) | YES | YES (fallthrough) | ✅ | free_entity → free_sched → … → put_heap |
| L691 | goto free_col_list (pm resume fail) | YES | YES (fallthrough) | ✅ | free_col_list → free_entity → … → put_heap |
| L696 | goto suspend_put (alloc resource fail) | YES | YES (fallthrough) | ✅ | suspend_put → free_col_list → … → put_heap |
| L704 | goto release_resource (map host buf fail) | YES | YES (double put likely) | ❌ EXCESS PUT | aie2_release_resource likely releases heap; then put_heap underflows refcount |
| L710 | goto release_resource (syncobj create fail) | YES | YES (double put likely) | ❌ EXCESS PUT | same double‑put pattern |
| L718 | success return 0 | YES | NO (ownership retained) | ✅ | heap reference stays with hwctx for later put in fini |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
aie2_hwctx_init() takes a reference on the dev_heap with drm_gem_object_get() and, on error paths after aie2_alloc_resource() succeeds, calls aie2_release_resource() (which likely releases the heap) then falls through to put_heap, causing a double put and an excess put warning.
```
