# REAL BUG: drivers/infiniband/hw/hfi1/file_ops.c:832 assign_ctxt()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

ut if callee already freed | **WARNING TRIGGER**: warn reports excess put at this deallocate_ctxt call. Indicates uctxt’s kref was 0 or object already freed, likely because setup_base_ctxt did its own cleanup or alloc never set refcount. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L781? (fd->uctxt check) | error | NO (no allocation) | N/A | ✅ | |
| L783? (size mismatch) | error | NO | N/A | ✅ | |
| L786? (copy_from_user fails) | error | NO | N/A | ✅ | |
| L789? (swmajor mismatch) | error | NO | N/A | ✅ | |
| L792? (subctxt_cnt too large) | error | NO | N/A | ✅ | |
| L798? ret=find_sub_ctxt error → default: break, return ret | error | NO (no alloc) | N/A | ✅ | |
| L798? ret=1 → case 1: complete_subctxt(success/error) | success/error | NO (no alloc) | N/A | ✅ | |
| L798? ret=0, allocate_ctxt error → default: break, return ret | error | NO (uctxt not valid) | N/A | ✅ | |
| L798? ret=0, allocate_ctxt success → case 0: setup_base_ctxt success | 0 | YES (conditional get taken) | NO (but ref held by assignment) | ✅ (refs managed by fd/ctxt lifecycle) | Initial alloc ref + get ref both held; assignment expected to consume both. |
| L798? ret=0, allocate_ctxt success → case 0: setup_base_ctxt error → deallocate_ctxt(uctxt) | error | ❓ (may or may not have taken get) | YES (unconditional kref_put) | ❌ EXCESS PUT if refcount=0, or double put if callee already freed | **WARNING TRIGGER**: warn reports excess put at this deallocate_ctxt call. Indicates uctxt’s kref was 0 or object already freed, likely because setup_base_ctxt did its own cleanup or alloc never set refcount. |

[NEED_SOURCE] setup_base_ctxt
[NEED_SOURCE] allocate_ctxt

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The call to deallocate_ctxt(uctxt) on the error path of setup_base_ctxt causes an excess kref_put because either setup_base_ctxt already released the reference (double put) or the initial reference from allocate_ctxt was never properly set (refcount 0). Without the callee sources this cannot be 100% certain, but the runtime warning of a refcount underflow strongly indicates a real double-free or use-after-free bug.
```
