# REAL BUG: arch/x86/kvm/mmu/tdp_mmu.c:1102 kvm_tdp_mmu_zap_invalidated_roots()

**Confidence**: HIGH | **Counter**: `$->tdp_mmu_root_count.refs.counter`

## Reasoning

m_tdp_mmu_put_root` for zapped roots.  This manual put is a **second put** on the same root, because the iterator will later (in its increment step) call `tdp_mmu_next_root(kvm, root)`, which will put this root again.  The result is an excess decrement – exactly the “refcount excess put” reported.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1076 (continue) | loop continue | YES (iterator’s get at top of loop) | YES (iterator’s step will put when advancing) | ✅ | Reference released by macro’s next call to `tdp_mmu_next_root` |
| L1102 (kvm_tdp_mmu_put_root) | in-loop manual put | YES (iterator’s get) | YES + EXTRA manual PUT | ❌ EXCESS PUT | Iterator will also put this same root on the next iteration step → double-put, refcount goes negative |
| End of function (line ~1110) | implicit void return | All references released by iterator if no bug | — | ✅ (macro balances final iteration) | No leak, but the double-put inside the loop corrupts the counter |

**Key observation:** The macro `for_each_tdp_mmu_root_yield_safe` uses `tdp_mmu_next_root`, which **acquires** a reference on every returned root and **releases** the previous root when moving to the next.  Inside the loop, the code does an unconditional `kvm_tdp_mmu_put_root` for zapped roots.  This manual put is a **second put** on the same root, because the iterator will later (in its increment step) call `tdp_mmu_next_root(kvm, root)`, which will put this root again.  The result is an excess decrement – exactly the “refcount excess put” reported.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The loop body calls `kvm_tdp_mmu_put_root` (L1102) after zapping, but the iterator (`for_each_tdp_mmu_root_yield_safe`) will put that root again when advancing to the next element, causing a double-put and refcount underflow.
```
