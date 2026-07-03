# REAL BUG: mm/mempolicy.c:1628 do_mbind()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

| `err==0`, list non-empty, but mode not interleaved → mpol_out | success | NO | N/A | ✅ | No get_vma_policy call |

## Full Response

```
| Path Description | Return Type | GET from get_vma_policy | PUT on that ref | Balanced? | Notes |
|------------------|-------------|--------------------------|------------------|-----------|-------|
| Early returns (flags, capability, alignment, end==start) | error / 0 | N/A | N/A | ✅ | Before any mpol get |
| mpol_new returns ERR_PTR | error | N/A | N/A | ✅ | Allocation failed |
| `goto mpol_out` from NODEMASK_SCRATCH error | error | NO | N/A | ✅ | No get_vma_policy call |
| `nr_failed < 0` → skip vma loop → mpol_out | error | NO | N/A | ✅ | No get_vma_policy call |
| vma loop, `mbind_range` fails, break → mpol_out | error | NO | N/A | ✅ | `!err` false, block skipped |
| `err==0` and `list_empty(&pagelist)` → mpol_out | success (0, no migration) | NO | N/A | ✅ | Block skipped |
| **`err==0`, list non-empty, mode == MPOL_INTERLEAVE/WEIGHTED_INTERLEAVE, enters block, calls `mpol_cond_put(get_vma_policy(...))`, then flows to `mpol_out`** | success | **YES** | **CONDITIONAL** (mpol_cond_put may skip) | ❌ **LEAK** if put skipped | `get_vma_policy` returns a reference that must be put; `mpol_cond_put` only puts under certain condition. If condition fails, ref is leaked. |
| `err==0`, list non-empty, but mode not interleaved → mpol_out | success | NO | N/A | ✅ | No get_vma_policy call |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`mpol_cond_put` conditionally releases the reference returned by `get_vma_policy`. When the condition fails, do_mbind leaks that reference because no other `mpol_put` is performed on it.
```
