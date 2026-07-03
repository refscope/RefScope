# REAL BUG: drivers/gpu/drm/drm_syncobj.c:516 drm_syncobj_find_fence()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| After wait loop (L493–L512 fall-through to out) | success/error | YES | YES (out: drm_syncobj_put) | ✅ | fence ref transferred via *fence = wait.fence |

## Full Response

```
| Line | Return Type | GET Done? (syncobj) | PUT Done? | Balanced? | Notes |
|------|-------------|---------------------|-----------|-----------|-------|
| L445 | error (-EINVAL) | YES if syncobj != NULL | NO | ❌ LEAK (when non-NULL) | drm_syncobj_find called before flag check; if handle valid, syncobj ref taken but not put |
| L448 | error (-ENOENT) | NO (syncobj == NULL) | N/A | ✅ | drm_syncobj_find returned NULL, no ref held |
| L465 (goto out via chain_find success) | success (ret=0) | YES | YES (out: drm_syncobj_put) | ✅ | fence returned to caller, no put on fence |
| L468 (chain_find failure → dma_fence_put, then no WAIT flag → goto out) | error | YES | YES (out: drm_syncobj_put) | ✅ | fence put already done |
| L470 (drm_syncobj_fence_get → NULL → ret=-EINVAL, no WAIT → goto out) | error | YES | YES (out: drm_syncobj_put) | ✅ | no fence ref held |
| After wait loop (L493–L512 fall-through to out) | success/error | YES | YES (out: drm_syncobj_put) | ✅ | fence ref transferred via *fence = wait.fence |

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`drm_syncobj_find()` acquires a reference (unconditional on non-NULL return), but the early `return -EINVAL` on invalid flags does not call `drm_syncobj_put(syncobj)`, leaking the syncobj reference whenever a valid handle is passed with bad flags.
```
