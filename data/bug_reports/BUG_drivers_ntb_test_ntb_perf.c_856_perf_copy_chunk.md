# REAL BUG: drivers/ntb/test/ntb_perf.c:856 perf_copy_chunk()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

- Success path after `dmaengine_submit()` calls `dmaengine_unmap_put()` to drop the driver’s own reference; the tx holds its reference and the callback handles it.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L809 | error (-ENOMEM) | NO (unmap NULL) | N/A | ✅ | |
| L815 | goto err_free_resource | YES (from get_unmap_data) | YES (at err_free_resource) | ✅ | |
| L828 | goto err_free_resource | YES | YES | ✅ | |
| L839 | goto err_free_resource | YES (two gets: initial + dma_set_unmap) | YES (single put) | ❌ **LEAK** | Only one put for two references; tx's reference not released |
| L846+return | success (ret==0) / error (-EINTR) | YES (two gets) | YES (one put for our ref, tx holds the other for callback) | ✅ | Balanced for this function's ownership; tx callback releases later |

**GET summary**:  
- `dmaengine_get_unmap_data()`: unconditional, sets refcount=1.  
- `dma_set_unmap()`: unconditional `kref_get`, adds another reference.

**Error path after `dma_set_unmap`**:  
`dmaengine_submit()` fails → `ret` non-zero → goto `err_free_resource`.  
At `err_free_resource`, only one `dmaengine_unmap_put(unmap)` is called. That releases the initial reference, but the extra reference from `dma_set_unmap` (now owned by the failed tx descriptor) is never released. The descriptor is not freed, and its callback will never fire, so the unmap reference remains leaked.

**Other paths are balanced**:  
- Before `dma_set_unmap`, error paths put exactly once.  
- Success path after `dmaengine_submit()` calls `dmaengine_unmap_put()` to drop the driver’s own reference; the tx holds its reference and the callback handles it.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`dma_submit_error` error path misses a second `dmaengine_unmap_put` for the reference added by `dma_set_unmap`, leaking the kref.
```
