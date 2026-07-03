# REAL BUG: drivers/iio/industrialio-buffer.c:1947 iio_buffer_enqueue_dmabuf()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1913 return ret (enqueue fail) | error | YES (init ref + add GET + iio_buffer_signal_dmabuf_done GET) | NO | ❌ LEAK | no put; extra signal get leaks as well |

## Full Response

```
| Line | Return Type | GET Done? (fence ref) | PUT Done? (fence put) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L1825 | early return -EFAULT | NO (before fence init) | N/A | ✅ | |
| L1830 | early return -EINVAL | NO | N/A | ✅ | |
| L1835 | early return -EINVAL | NO | N/A | ✅ | |
| L1840 | IS_ERR(dmabuf) return | NO | N/A | ✅ | |
| L1843 goto err_dmabuf_put | error | NO | NO (only dma_buf_put) | ✅ | |
| L1849 goto err_dmabuf_put | error | NO | NO | ✅ | |
| L1857 goto err_attachment_put | error | NO | NO (only iio_buffer_dmabuf_put) | ✅ | |
| L1871 goto err_fence_put | error | YES (init ref) | YES (dma_fence_put at err_fence_put) | ✅ | |
| L1883 goto err_resv_unlock | error | YES | YES (via err_resv_unlock → err_fence_put) | ✅ | |
| L1893 goto err_queue_unlock | error | YES | YES (via err_queue_unlock → err_resv_unlock → err_fence_put) | ✅ | |
| L1913 return ret (success) | success | YES (init ref + dma_resv_add_fence GET) | NO | ❌ LEAK | dma_fence_put never called after add |
| L1913 return ret (enqueue fail) | error | YES (init ref + add GET + iio_buffer_signal_dmabuf_done GET) | NO | ❌ LEAK | no put; extra signal get leaks as well |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
dma_resv_add_fence and iio_buffer_signal_dmabuf_done both unconditionally get fence references but no matching dma_fence_put is performed on the success path or the enqueue-failure error path, leaking the initial reference and any additional gets.
```
