# REAL BUG: drivers/ntb/ntb_transport.c:1579 ntb_async_rx_submit()

**Confidence**: HIGH | **Counter**: `unmap->kref.refcount.refs.counter`

## Reasoning

| L1568 | success return | YES (2 refs held) | YES (dmaengine_unmap_put once, ref=2→1) | ✅ | remaining ref freed by DMA callback |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1528 | goto err    | NO (before any GET) | N/A | ✅ | |
| L1533 | goto err    | NO (unmap alloc failed) | N/A | ✅ | |
| L1539 | goto err_get_unmap | YES (1 ref from dmaengine_get_unmap_data) | YES (dmaengine_unmap_put once) | ✅ | ref 1 → 0 |
| L1545 | goto err_get_unmap | YES | YES | ✅ | ref 1 → 0 |
| L1551 | goto err_get_unmap | YES | YES | ✅ | ref 1 → 0 |
| L1558↗| (after dma_set_unmap) | YES (ref becomes 2) | - | - | dma_set_unmap adds kref_get |
| L1563↘| goto err_set_unmap | YES (2 refs held) | YES (dmaengine_unmap_put once, ref=2→1) | ❌ LEAK | descriptor ref not freed, unmap ref not released |
| L1568 | success return | YES (2 refs held) | YES (dmaengine_unmap_put once, ref=2→1) | ✅ | remaining ref freed by DMA callback |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After dma_set_unmap(), the unmap holds 2 references. On dma_submit_error(), err_set_unmap calls dmaengine_unmap_put() only once, leaving a dangling reference from dma_set_unmap.
```
