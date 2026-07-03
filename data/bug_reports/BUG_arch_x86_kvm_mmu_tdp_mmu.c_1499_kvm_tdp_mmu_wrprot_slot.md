# REAL BUG: arch/x86/kvm/mmu/tdp_mmu.c:1499 kvm_tdp_mmu_wrprot_slot()

**Confidence**: MEDIUM | **Counter**: `$->tdp_mmu_root_count.refs.counter`

## Reasoning

ing site). | ❌ If no TDP MMU root exists for the slot, the loop body never executes, no GET is performed, but the macro unconditionally calls `kvm_tdp_mmu_put_root()` (or equivalent) on the last root, causing an excess put on `tdp_mmu_root_count`. | Warning is “refcount excess put” at line 1499. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 1497 | `return spte_set;` | GETs happen inside `for_each_valid_tdp_mmu_root_yield_safe` only if the iterator yields a root (via `tdp_mmu_next_root`). | The macro releases the last root after the loop (line 1499, warning site). | ❌ If no TDP MMU root exists for the slot, the loop body never executes, no GET is performed, but the macro unconditionally calls `kvm_tdp_mmu_put_root()` (or equivalent) on the last root, causing an excess put on `tdp_mmu_root_count`. | Warning is “refcount excess put” at line 1499. |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
The `for_each_valid_tdp_mmu_root_yield_safe` macro has an unconditional final put after the loop, but when the list is empty, no get was performed, leading to an excess put on the root refcount. This is consistent with the Smatch warning.
```
