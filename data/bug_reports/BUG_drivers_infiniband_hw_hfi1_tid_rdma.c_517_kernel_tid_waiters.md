# REAL BUG: drivers/infiniband/hw/hfi1/tid_rdma.c:517 kernel_tid_waiters()

**Confidence**: LOW | **Counter**: `$->refcount.counter`

## Reasoning

| L517 | return bool | NO (first_qp does not appear to take a reference) | YES (rvt_put_qp unconditionally called) | ❌ EXCESS PUT | Put without corresponding get — warning confirms excess put on refcount. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L517 | return bool | NO (first_qp does not appear to take a reference) | YES (rvt_put_qp unconditionally called) | ❌ EXCESS PUT | Put without corresponding get — warning confirms excess put on refcount. |

[NEED_SOURCE] first_qp

VERDICT: REAL_BUG
CONFIDENCE: LOW

rvt_put_qp(fqp) is called unconditionally, but first_qp() likely does not increment the reference count (name gives no hint of a get). The static analysis flags an excess put, consistent with a missing get.
```
