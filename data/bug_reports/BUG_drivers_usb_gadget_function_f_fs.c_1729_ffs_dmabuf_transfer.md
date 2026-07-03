# REAL BUG: drivers/usb/gadget/function/f_fs.c:1729 ffs_dmabuf_transfer()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

e (typical naming suggests it only signals, not puts), this is a reference leak. The success path may be safe if `ffs_epfile_dmabuf_io_complete` (the completion handler) eventually calls `dma_fence_put()`, but the failure path certainly leaks the extra reference obtained by `dma_resv_add_fence()`.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1607 | error (`return -EINVAL`) | NO (before get) | N/A | ✅ | flags check before any ref |
| L1610 | IS_ERR guard (`return PTR_ERR(dmabuf)`) | NO (get failed) | N/A | ✅ | dma_buf_get returns ERR_PTR, no ref held |
| L1613–1615 | `goto err_dmabuf_put` | NO (only dma_buf_get) | YES (dma_buf_put at label) | ✅ | length check, releases dmabuf |
| L1619 | `goto err_dmabuf_put` | NO | YES | ✅ | attach IS_ERR, releases dmabuf |
| L1626 | `goto err_attachment_put` | NO | YES (ffs_dmabuf_put(attach) + dmabuf) | ✅ | ep IS_ERR, releases attach + dmabuf |
| L1631 | `goto err_attachment_put` | NO | YES | ✅ | dma_resv_lock fails, releases attach + dmabuf |
| L1640 | `goto err_resv_unlock` | NO | YES (dma_resv_unlock + attach + dmabuf) | ✅ | resv wait timeout/error |
| L1647 | `goto err_resv_unlock` | NO | YES | ✅ | reserve_fences fails |
| L1652 | `goto err_resv_unlock` | NO | YES | ✅ | kmalloc_obj fence fails, no fence yet |
| L1659 | `goto err_fence_put` | YES (fence allocated & init) | YES (dma_fence_put) | ✅ | ep changed, releases fence + others |
| L1665 | `goto err_fence_put` | YES | YES | ✅ | usb_ep_alloc_request fails, releases fence |
| L1686 (after dma_resv_add_fence) | **success** (`return ret` after queue ok) | **YES** (unconditional get from add_fence) | **UNCLEAR** (no explicit put; possible ownership transfer to request if completion handler puts) | ⚠️ Potentially balanced if completion handler does put | GET from add_fence; initial ref may be moved to request |
| L1692 (queue failure else) | **error** (`return ret`) | **YES** (unconditional get from add_fence) | **NO** (no dma_fence_put; ffs_dmabuf_signal_done may not put) | ❌ LEAK | Queue failed → request freed, no completion handler, fence ref not released |

> **Note**: `dma_resv_add_fence()` is documented as an unconditional get (see contract). After this call, the refcount of the fence is incremented. On the **queue‐failure** path, the request is not queued, the completion handler will never fire, and the code does **not** call `dma_fence_put()`. Unless `ffs_dmabuf_signal_done()` internally releases the reference (typical naming suggests it only signals, not puts), this is a reference leak. The success path may be safe if `ffs_epfile_dmabuf_io_complete` (the completion handler) eventually calls `dma_fence_put()`, but the failure path certainly leaks the extra reference obtained by `dma_resv_add_fence()`.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After `dma_resv_add_fence()` (unconditional get), the `usb_ep_queue` failure path returns without `dma_fence_put()`, leaking the reference on the fence when the request is not queued and no completion handler will run.
```
