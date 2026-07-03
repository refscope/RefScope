# REAL BUG: arch/x86/kvm/../../../virt/kvm/kvm_main.c:1230 kvm_create_vm()

**Confidence**: HIGH | **Counter**: `$->mm_count.counter`

## Reasoning

| Success path | (return `kvm`) | YES | NO (not called) | NO (ref kept) | ✅ | kvm holds reference |

## Full Response

```
| Path Origin (Condition) | goto Label | GET Done? | PUT (mmu_notifier_unregister)? | PUT (mmdrop)? | Balanced? | Notes |
|--------------------------|------------|-----------|-------------------------------|---------------|-----------|-------|
| `!kvm` after alloc | (early return) | NO | N/A | N/A | ✅ | Before get |
| `init_srcu_struct(&kvm->srcu)` fails | `out_err_no_srcu` | YES | NO | YES (direct) | ✅ | Single mmdrop |
| `init_srcu_struct(&kvm->irq_srcu)` fails | `out_err_no_irq_srcu` → `out_err_no_srcu` | YES | NO | YES (cascade) | ✅ | Single mmdrop |
| `kvm_init_irq_routing()` fails | `out_err_no_irq_routing` → `… → out_err_no_srcu` | YES | NO | YES (cascade) | ✅ | Single mmdrop |
| bus `kzalloc` fails | `out_err_no_arch_destroy_vm` → `… → out_err_no_srcu` | YES | NO | YES (cascade) | ✅ | Single mmdrop |
| `kvm_arch_init_vm()` fails | `out_err_no_arch_destroy_vm` → `… → out_err_no_srcu` | YES | NO | YES (cascade) | ✅ | Single mmdrop |
| `kvm_enable_virtualization()` fails | `out_err_no_disable` → `… → out_err_no_srcu` | YES | NO | YES (cascade) | ✅ | Single mmdrop |
| `kvm_init_mmu_notifier()` fails | `out_err_no_mmu_notifier` → `… → out_err_no_srcu` | YES | NO (skipped, ops=NULL) | YES (cascade) | ✅ | No double put |
| `kvm_coalesced_mmio_init()` fails (notifier success) | `out_no_coalesced_mmio` → `… → out_err_no_srcu` | YES | **YES** (mmu_notifier_unregister) | **YES** (cascade) | ❌ **EXCESS** | Double PUT |
| `kvm_create_vm_debugfs()` fails (notifier success) | `out_err_no_debugfs` → `out_no_coalesced_mmio` → `… → out_err_no_srcu` | YES | **YES** (mmu_notifier_unregister) | **YES** (cascade) | ❌ **EXCESS** | Double PUT |
| Success path | (return `kvm`) | YES | NO (not called) | NO (ref kept) | ✅ | kvm holds reference |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
mmgrab at start, error paths after successful kvm_init_mmu_notifier call both mmu_notifier_unregister (which drops mm) and mmdrop, causing refcount excess put.
```
