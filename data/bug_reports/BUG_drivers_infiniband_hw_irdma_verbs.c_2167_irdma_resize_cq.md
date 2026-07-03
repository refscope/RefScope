# REAL BUG: drivers/infiniband/hw/irdma/verbs.c:2167 irdma_resize_cq()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L2157 | return 0    | YES (alloc) + handle balanced | YES (caller put + handle put) | ✅ | success path, both caller and handle drop refs |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2043 | EOPNOTSUPP  | NO (before get) | N/A | ✅ | feature check |
| L2046 | EINVAL      | NO (before get) | N/A | ✅ | udata length check |
| L2049 | EINVAL      | NO (before get) | N/A | ✅ | entries too large |
| L2069 | 0           | NO (before get) | N/A | ✅ | size unchanged |
| L2078 | EOPNOTSUPP  | NO (before get) | N/A | ✅ | legacy mode |
| L2082 | EINVAL      | NO (before get) | N/A | ✅ | copy_from_udata fail |
| L2090 | ENOMEM      | NO (before get) | N/A | ✅ | iwpbl_buf NULL |
| L2110 | ENOMEM      | NO (before get) | N/A | ✅ | dma_alloc_coherent fail |
| L2117 | goto error  | NO (before get) | N/A | ✅ | cq_buf alloc fail |
| L2124 | goto error  | NO (get returned NULL) | N/A | ✅ | cqp_request NULL |
| L2141 | goto error  | YES (from alloc_and_get) + YES (possible from irdma_handle_cqp_op) | caller PUT done (YES), but internal handle may miss PUT on error | ❌ LEAK | irdma_handle_cqp_op may take extra ref without releasing → one ref remains after caller's put |
| L2157 | return 0    | YES (alloc) + handle balanced | YES (caller put + handle put) | ✅ | success path, both caller and handle drop refs |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The error path after `irdma_handle_cqp_op` returns via `goto error` (L2141→L2166), where the caller has already released its own reference but `irdma_handle_cqp_op` may have taken an additional reference internally without a matching put, leaving the CQP request with an unreleased reference count.
```
