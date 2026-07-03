# REAL BUG: drivers/scsi/esas2r/esas2r_init.c:430 esas2r_init_adapter()

**Confidence**: HIGH | **Counter**: `$->dis_ints_cnt.counter`

## Reasoning

| L385 (success) | return 1 | YES (L333) | YES (twice: inside `esas2r_claim_interrupts` and explicit `esas2r_enable_chip_interrupts` at L379) | ❌ EXCESS PUT | Double enable → decrements `dis_ints_cnt` twice, causing underflow |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L271 (early inv idx) | return 0 | NO | N/A | ✅ | before any get |
| L276 (existing adapt) | return 0 | NO | N/A | ✅ | before any get |
| L288 (DMA mask fail) | return 0 | NO | N/A | ✅ | before any get |
| L323 (VDA alloc fail) | return 0 | NO | N/A | ✅ | before get (increment at L333 after this) |
| L331 (map regions fail) | return 0 | NO | N/A | ✅ | before get |
| L353 (uncached NULL) | return 0 | YES (L333) | NO | ❌ LEAK | gen leak, not the warning |
| L367 (init_adapter_struct fail) | return 0 | YES (L333) | NO | ❌ LEAK | gen leak, not the warning |
| L385 (success) | return 1 | YES (L333) | YES (twice: inside `esas2r_claim_interrupts` and explicit `esas2r_enable_chip_interrupts` at L379) | ❌ EXCESS PUT | Double enable → decrements `dis_ints_cnt` twice, causing underflow |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`esas2r_claim_interrupts(a)` internally enables chip interrupts (decrements `dis_ints_cnt`), then init_adapter unconditionally calls `esas2r_enable_chip_interrupts` again when IRQ_CLAIMED is set, resulting in a double put that makes the counter go negative.
```
