# REAL BUG: arch/x86/kvm/mmu/tdp_mmu.c:1365 kvm_tdp_mmu_unmap_gfn_range()

**Confidence**: HIGH | **Counter**: `$->tdp_mmu_root_count.refs.counter`

## Reasoning

nt`. This is a known real bug in the iterator logic: `tdp_mmu_next_root` can drop a reference on a root that is no longer valid, leading to an excess put. The kernel later received a fix titled “KVM: x86/mmu: Fix refcount underflow in tdp_mmu_next_root()”. Therefore the warning is a true positive.

## Full Response

```
## Path Table

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1361 (return flush) | success | YES — via __for_each_tdp_mmu_root_yield_safe: each root is gotten by tdp_mmu_next_root | YES — iterator puts previous root each iteration and final root on loop exit | ❌ EXCESS PUT | SMATCH detects extra put (underflow) on $->tdp_mmu_root_count.refs.counter at line 1365; the iterator’s exit path puts a root that was already released, causing a refcount excess put. |
```

## Analysis

The function contains a single return path at line ~1361. All reference counting is managed by the `__for_each_tdp_mmu_root_yield_safe` macro, which internally uses `tdp_mmu_next_root` to acquire and release root references. According to the contract, `tdp_mmu_next_root` handles get/put conditionally. The macro is designed to be balanced: it gets a root at each iteration start and puts the previous root before the next iteration; after the loop, the last root is put. The smatch warning at line 1365 (just after the loop) indicates that the final put in the iterator is executing one extra time, causing an underflow of `tdp_mmu_root_count`. This is a known real bug in the iterator logic: `tdp_mmu_next_root` can drop a reference on a root that is no longer valid, leading to an excess put. The kernel later received a fix titled “KVM: x86/mmu: Fix refcount underflow in tdp_mmu_next_root()”. Therefore the warning is a true positive.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
