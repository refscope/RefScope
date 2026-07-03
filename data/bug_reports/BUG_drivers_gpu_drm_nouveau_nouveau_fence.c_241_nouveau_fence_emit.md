# REAL BUG: drivers/gpu/drm/nouveau/nouveau_fence.c:241 nouveau_fence_emit()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

EAK (fctx→fence_ref) | fctx→fence_ref taken unconditionally, no put on emit failure |

## Full Response

```
| Line | Return Type | GET (fctx→fence_ref) Done? | PUT (fctx→fence_ref) Done? | dma_fence GET Done? | dma_fence PUT Done? | Balanced? | Notes |
|------|-------------|----------------------------|----------------------------|---------------------|---------------------|-----------|-------|
| L233 | error (killed) | YES (L223) | NO | YES (L227) | YES (L232) | ❌ LEAK (fctx→fence_ref) | dma_fence balanced, but fctx→fence_ref not released |
| L241 | error (ret≠0) | YES (L223) | NO | NO (not called) | N/A | ❌ LEAK (fctx→fence_ref) | fctx→fence_ref taken unconditionally, no put on emit failure |
| L241 | success (ret=0) | YES (L223) | NO (held for pending list) | YES (L227) | NO (transferred to list) | ✅ (intentional) | fctx→fence_ref held until fence destroyed; dma_fence ref owned by fctx→pending list |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`kref_get(&fctx->fence_ref)` at L223 is unconditional; the error path (ret≠0) and the killed path (L233) return without `kref_put`, leaking the fence channel reference.
```
