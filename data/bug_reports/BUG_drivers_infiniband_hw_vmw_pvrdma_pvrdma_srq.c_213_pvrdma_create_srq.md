# REAL BUG: drivers/infiniband/hw/vmw_pvrdma/pvrdma_srq.c:213 pvrdma_create_srq()

**Confidence**: HIGH | **Counter**: `srq->refcnt.refs.counter`

## Reasoning

| L191 | error (ib_copy_to_udata fails) | YES | YES (pvrdma_destroy_srq) | ✅ | explicit destroy on copy-to-user failure |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L116 | error | NO (before get) | N/A | ✅ | return -EOPNOTSUPP; early check |
| L122 | error | NO | N/A | ✅ | return -EOPNOTSUPP; early check |
| L129 | error | NO | N/A | ✅ | return -EINVAL; early check |
| L133 | error | NO | N/A | ✅ | atomic_add_unless fails, return -ENOMEM |
| L142 → err_srq | error (goto) | YES (refcount_set at L137) | NO | ❌ LEAK | ib_copy_validate_udata_in fails, err_srq only does atomic_dec, no srq put |
| L147 → err_srq | error (goto) | YES | NO | ❌ LEAK | IS_ERR(srq->umem), err_srq lacks srq release |
| L157 → err_umem | error (goto) | YES | NO | ❌ LEAK | pages overflow, err_umem → ib_umem_release → err_srq, no srq put |
| L162 → err_umem | error (goto) | YES | NO | ❌ LEAK | page_dir_init fails, same cleanup chain, no srq put |
| L177 → err_page_dir | error (goto) | YES | NO | ❌ LEAK | cmd_post fails, err_page_dir → err_umem → err_srq, still no srq put |
| L191 | error (ib_copy_to_udata fails) | YES | YES (pvrdma_destroy_srq) | ✅ | explicit destroy on copy-to-user failure |
| L195 | success | YES | YES (held in srq_tbl) | ✅ | srq alive, will be destroyed later |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After refcount_set at L137, five error paths (L142, L147, L157, L162, L177) jump to labels that only release umem, page_dir, and decrement num_srqs, but never call pvrdma_destroy_srq to release the initial srq reference.
```
