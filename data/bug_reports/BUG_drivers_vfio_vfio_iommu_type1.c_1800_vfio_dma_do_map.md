# REAL BUG: drivers/vfio/vfio_iommu_type1.c:1800 vfio_dma_do_map()

**Confidence**: HIGH | **Counter**: `dma->mm->mm_count.counter`

## Reasoning

| L1777 (success, no dirty tracking or domain_list empty) | return 0 | YES | N/A (held for lifetime) | ✅ | dma linked, freed later via dma unmap |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1685 | error | NO (before get) | N/A | ✅ | overflow check |
| L1688 | error | NO (before get) | N/A | ✅ | size == 0 |
| L1691 | error | NO (before get) | N/A | ✅ | overflow check |
| L1708 | goto out_unlock | NO (before get) | N/A | ✅ | alignment check |
| L1715‑1724 | goto out_unlock | NO (before get) | N/A | ✅ | set_vaddr paths |
| L1729 | goto out_unlock | NO (before get) | N/A | ✅ | dma already exists |
| L1734 | goto out_unlock | NO (before get) | N/A | ✅ | dma_avail exhausted |
| L1739 | goto out_unlock | NO (before get) | N/A | ✅ | invalid iova |
| L1744 | goto out_unlock | NO (before get) | N/A | ✅ | kzalloc failed |
| L1765 (mmgrab) | – | YES | – | – | ref acquired |
| **L1773 (vfio_pin_map_dma fails)** | goto out_unlock | YES | ❌ NO | **❌ LEAK** | no vfio_remove_dma on pin error |
| L1777 (bitmap_alloc fails) | ret error through out_unlock | YES | YES (vfio_remove_dma) | ✅ | dma removed, mm put |
| L1777 (success, no dirty tracking or domain_list empty) | return 0 | YES | N/A (held for lifetime) | ✅ | dma linked, freed later via dma unmap |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
mmgrab at L1765, if vfio_pin_map_dma fails the code goes to out_unlock without calling vfio_remove_dma, leaking the mm_struct reference.
```
