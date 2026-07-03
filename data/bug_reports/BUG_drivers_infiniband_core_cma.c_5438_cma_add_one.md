# REAL BUG: drivers/infiniband/core/cma.c:5438 cma_add_one()

**Confidence**: MEDIUM | **Counter**: `cma_dev->refcount.refs.counter`

## Reasoning

protects the object but the object is used after release. |
| L5443| success     | YES (refcount held for device lifetime) | NO (held) | ✅ | Device is kept; ref released later in cma_remove_one. |
```

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~5368| early return| NO (before any get) | N/A | ✅ | |
| ~5372| error       | NO (allocation failed) | N/A | ✅ | |
| ~5379| goto free_cma_dev | NO (before refcount_set) | N/A | ✅ | |
| ~5385| goto free_gid_type | NO (before refcount_set) | N/A | ✅ | |
| L5438| refcount_set executes, subsequent error path via `goto free_listen` | YES (refcount_set sets to 1) | YES (cma_process_remove does cma_dev_put) | ❌ **Real bug** | After PUT, code accesses cma_dev->default_roce_tos, cma_dev->default_gid_type, and kfree(cma_dev) — use-after-free/double-free. Refcount protects the object but the object is used after release. |
| L5443| success     | YES (refcount held for device lifetime) | NO (held) | ✅ | Device is kept; ref released later in cma_remove_one. |
```

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
refcount_set initializes refcount to 1; on error path, cma_process_remove releases it, but the function continues to access and free cma_dev, causing use-after-free/double-free.
```
