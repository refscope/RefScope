# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_ttm.c:2589 amdgpu_ttm_clear_buffer()

**Confidence**: HIGH | **Counter**: `*fence->refcount.refcount.refs.counter`

## Reasoning

| fill_mem fails → `goto err` → `return r`              | error       | YES       | NO        | ❌ LEAK   | *fence still holds ref from dma_fence_get_stub() or previous success  |

## Full Response

```
```
| Path Description                                       | Return Type | GET Done? | PUT Done? | Balanced? | Notes                                                                 |
|--------------------------------------------------------|-------------|-----------|-----------|-----------|-----------------------------------------------------------------------|
| Early return (!buffer_funcs_enabled)                   | error       | NO        | N/A       | ✅        | Before *fence assignment                                              |
| Early return (!fence)                                  | error       | NO        | N/A       | ✅        | Before *fence assignment                                              |
| While loop ends (r==0), *fence handed to caller        | success     | YES       | caller    | ✅        | Last *fence passed to caller, caller will put                         |
| map_buffer fails → `goto err` → `return r`            | error       | YES       | NO        | ❌ LEAK   | *fence still holds ref from dma_fence_get_stub() or previous success  |
| fill_mem fails → `goto err` → `return r`              | error       | YES       | NO        | ❌ LEAK   | *fence still holds ref from dma_fence_get_stub() or previous success  |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`dma_fence_get_stub()` unconditionally acquires a reference into `*fence`; error paths from `amdgpu_ttm_map_buffer`/`amdgpu_ttm_fill_mem` jump to `err` and return without `dma_fence_put`, leaking the fence reference.
```
```
