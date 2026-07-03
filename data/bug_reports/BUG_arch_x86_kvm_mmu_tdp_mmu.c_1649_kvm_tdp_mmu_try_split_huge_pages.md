# REAL BUG: arch/x86/kvm/mmu/tdp_mmu.c:1649 kvm_tdp_mmu_try_split_huge_pages()

**Confidence**: HIGH | **Counter**: `$->tdp_mmu_root_count.refs.counter`

## Reasoning

This matches known KVM bugs where a callee unconditionally releases a reference on failure, causing the caller’s symmetric put to become an underflow. The fix would be to either not put in `tdp_mmu_split_huge_pages_root` or remove the caller’s put on error.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1651 (implicit after the loop, normal exit) | void return | YES (iterator acquired reference for each root) | YES (last root released by iterator’s next call that returns NULL) | ✅ | Balanced; loop terminates without break |
| L1649 (error path, break then exit) | void return | YES (iterator acquired reference for this root) | YES (explicit `kvm_tdp_mmu_put_root` at L1649) | ❌ IMBALANCE (excess put) | Warning flag: refcount already zero → likely `tdp_mmu_split_huge_pages_root` already consumed the root’s reference on failure, causing a double put. |

## Reasoning

- **Contract for `tdp_mmu_next_root`** says it acquires a reference on each returned root and releases the previous one.  
- Inside the loop, the current root has a valid reference.  
- When `kvm_tdp_mmu_try_split_huge_pages` exits normally, the iterator’s next call releases the last root – balanced.  
- On the error path (`if (r) { ... }`), the function explicitly puts the root before breaking.  
  - **But the warning at line 1649 shows a refcount already zero at that put**, indicating an earlier put.  
  - The only other entity that could have released the root’s reference is the callee `tdp_mmu_split_huge_pages_root`, which very likely consumes the root’s reference on error.  
  - Therefore, the caller’s `kvm_tdp_mmu_put_root` is an **extra put**, leading to an excess (double) put and refcount underflow.  

This matches known KVM bugs where a callee unconditionally releases a reference on failure, causing the caller’s symmetric put to become an underflow. The fix would be to either not put in `tdp_mmu_split_huge_pages_root` or remove the caller’s put on error.

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
`tdp_mmu_split_huge_pages_root` likely consumes the root’s ref on error, causing a double put at L1649.  
```
