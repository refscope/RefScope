# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_sync.c:266 amdgpu_sync_resv()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| ~264 | success (`return 0;`) | YES (all outer references from the iterator) | NO (none of the outer refs were put in the loop) | ❌ LEAK | Final return without releasing any of the outer fences' references |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~248 | error       | NO (before any iter) | N/A  | ✅ | NULL resv, early return |
| ~259 | error (inner `return r;`) | YES (outer reference from `dma_resv_for_each_fence` + inner chain's `dma_fence_get` was put, but outer ref not put) | NO for outer ref | ❌ LEAK | Outer reference held by iterator never released; inner loop's extra ref was put, but outer ref leaks |
| ~264 | success (`return 0;`) | YES (all outer references from the iterator) | NO (none of the outer refs were put in the loop) | ❌ LEAK | Final return without releasing any of the outer fences' references |

**PRE-VERDICT CHECKLIST**  
1. **"Held for device lifetime"?** No — the fence references are not stored long‑term; they are discarded after the loop.  
2. **"Ownership transferred"?** No — the outer fence reference is never given to any cleanup function; the iterator gives a ref that the caller must release.  
3. **Unconditional GET?** The `dma_resv_for_each_fence` iterator unconditionally returns each fence with an additional reference (a GET), and the code has no corresponding `dma_fence_put`.  
4. **`goto out` between GET and PUT?** Not applicable, but analogous: the inner `return r;` and the final `return 0;` skip the required put of the outer fence reference.

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
The `dma_resv_for_each_fence` iterator returns each fence with a reference that must be released by `dma_fence_put()`, but the function never calls `dma_fence_put()` on the outer fence—only managing the inner chain reference—causing a refcount leak on every fence iterated.
```
