# REAL BUG: drivers/accel/amdxdna/amdxdna_gem.c:474 amdxdna_gem_dmabuf_mmap()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| return 0 (success) | success | YES | NO | ❌ LEAK | Success path lacks drm_gem_object_put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| goto put_obj (after drm_gem_shmem_mmap fail) | error | YES | YES (via put_obj) | ✅ | Error path, put called |
| goto close_vma → put_obj (after vm_insert_pages fail) | error | YES | YES (via close_vma fall‑through) | ✅ | Error path, close and put called |
| return 0 (success) | success | YES | NO | ❌ LEAK | Success path lacks drm_gem_object_put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`drm_gem_object_get` is unconditional; the success path (return 0) does not call `drm_gem_object_put`, leaking a reference. Error paths do correctly release the reference, causing the inconsistent refcounting flagged by the warning.
```
