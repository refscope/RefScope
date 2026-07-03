# REAL BUG: drivers/infiniband/core/verbs.c:990 ib_create_ah_from_wc()

**Confidence**: MEDIUM | **Counter**: `$->grh.sgid_attr.entry.kref.refcount.refs.counter`

## Reasoning

| L990 (ah is valid) | success     | YES (rdma_fill_sgid_attr get is done) | YES (ref is stored in ah and will be released on ah destruction, rdma_destroy_ah_attr releases init ref) | ✅ | Ref held by ah for its lifetime; no leak in function |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L983 (ret != 0) | error       | NO (ib_init_ah_attr_from_wc failed → no ref obtained from init) | N/A | ✅ | Conditional get; error means no ref held |
| L990 (ah is ERR_PTR) | error       | YES (rdma_create_ah unconditionally calls rdma_fill_sgid_attr, which gets sgid_attr ref) | NO (if rdma_create_ah fails and does not call rdma_unfill_sgid_attr, the ref is leaked; caller does not release it) | ❌ LEAK | Error path after init success but ah creation failure; net refcount bump leaks |
| L990 (ah is valid) | success     | YES (rdma_fill_sgid_attr get is done) | YES (ref is stored in ah and will be released on ah destruction, rdma_destroy_ah_attr releases init ref) | ✅ | Ref held by ah for its lifetime; no leak in function |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

rdma_create_ah unconditionally increments sgid_attr via rdma_fill_sgid_attr; if it later fails and returns ERR_PTR without unwinding that get (rdma_unfill_sgid_attr), the caller has no way to release the extra reference, and it leaks. The warning at line 990 flags the return after rdma_destroy_ah_attr where the leaked reference persists. Success path is balanced because the ah retains the ref.
```
