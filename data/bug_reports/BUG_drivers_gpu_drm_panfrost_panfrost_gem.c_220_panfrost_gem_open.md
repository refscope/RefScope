# REAL BUG: drivers/gpu/drm/panfrost/panfrost_gem.c:220 panfrost_gem_open()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L219 | success       | YES (L184, L197)     | N/A (transferred)      | ✅         | On success (ret=0) the mapping is added to list; mapping now owns the refs and will release them on eventual removal (release callback). Not flagged; leak only on error paths.                      |

## Full Response

```
| Line | Return Type  | GET Done? (obj+mmu) | PUT Done? (on obj+mmu) | Balanced? | Notes                                                                                                                                                                                                |
|------|---------------|----------------------|------------------------|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L180 | error         | NO (before gets)     | N/A                    | ✅         | Before any ref acquire, mapping allocation failed.                                                                                                                                                  |
| L203 | goto err      | YES (L184, L197)     | NO (only mapping put)  | ❌ LEAK    | drm_gem_object_get + panfrost_mmu_ctx_get both unconditional; err label only calls panfrost_gem_mapping_put, no drm_gem_object_put or panfrost_mmu_ctx_put visible.                                 |
| L208 | goto err      | YES (L184, L197)     | NO (only mapping put)  | ❌ LEAK    | Same as above; after panfrost_mmu_map failure, mapping put called but gem and mmu references leaked.                                                                                                 |
| L219 | success       | YES (L184, L197)     | N/A (transferred)      | ✅         | On success (ret=0) the mapping is added to list; mapping now owns the refs and will release them on eventual removal (release callback). Not flagged; leak only on error paths.                      |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Both `drm_gem_object_get` (L184) and `panfrost_mmu_ctx_get` (L197) are unconditional gets. The error paths via `goto err` at L203 and L208 only call `panfrost_gem_mapping_put(mapping)` (which releases the mapping's own kref), but do not call `drm_gem_object_put()` or `panfrost_mmu_ctx_put()`. The provided contracts contain no evidence that `panfrost_gem_mapping_put` internally releases these references, and the warning directly flags the refcount leak on the returned counter. Therefore, the gem object and MMU context references acquired in this function are never released on error, constituting a genuine refcount leak.
```
