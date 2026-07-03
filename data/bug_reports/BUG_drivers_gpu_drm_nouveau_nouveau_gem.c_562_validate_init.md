# REAL BUG: drivers/gpu/drm/nouveau/nouveau_gem.c:562 validate_init()

**Confidence**: HIGH | **Counter**: `gem->refcount.refcount.refs.counter`

## Reasoning

| After loop (failure, ret != 0) | error (return ret) | YES (gems previously added to lists) | YES (validate_fini cleans lists) | ✅ for listed gems; ❌ for the current gem if break occurred before list add (as above) | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L470 (trycnt > 100000) | error (return -EINVAL) | NO (no gem lookup) | N/A | ✅ | |
| L487 break (Unknown handle) | error (ret -ENOENT) | NO (gem = NULL) | N/A | ✅ | |
| L493 continue (res_bo duplicate) | continue | YES (gem != NULL) | YES (drm_gem_object_put) | ✅ | |
| L501 break (multiple instances, put before break) | error (ret -EINVAL) | YES | YES (drm_gem_object_put) | ✅ | |
| L510–L530 break after ttm_bo_reserve failure (non‑EDEADLK or slowpath failure) | error (break, then after‑loop cleanup) | YES | NO | ❌ LEAK | Current gem not added to any list, no explicit put; previous list items moved to op→list and cleaned |
| L540 break after “vma not found!” | error (ret -EINVAL) | YES | NO | ❌ LEAK | gem reserved but not added to any list, no put |
| L545 break after invalid valid_domains (added to both_list) | error (ret -EINVAL) | YES | YES (via list_add → splice → validate_fini) | ✅ | |
| After loop (success, ret == 0) | success | YES (all gems added to lists) | YES (validate_fini cleans lists) | ✅ | |
| After loop (failure, ret != 0) | error (return ret) | YES (gems previously added to lists) | YES (validate_fini cleans lists) | ✅ for listed gems; ❌ for the current gem if break occurred before list add (as above) | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
drm_gem_object_lookup acquires a reference; two break paths (ttm_bo_reserve failure‑non‑EDEADLK and “vma not found”) exit the loop without adding the gem to a list and without calling drm_gem_object_put, leaking the reference.
```
