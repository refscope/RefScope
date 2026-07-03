# REAL BUG: drivers/infiniband/hw/hfi1/tid_rdma.c:844 hfi1_kern_clear_hw_flow()

**Confidence**: LOW | **Counter**: `$->refcount.counter`

## Reasoning

If that is the case, calling `rvt_put_qp(fqp)` on the **same QP** path is an **excess put**—exactly the warning reported.

## Full Response

```
[NEED_SOURCE] first_qp
[NEED_SOURCE] rvt_put_qp
[NEED_SOURCE] tid_rdma_schedule_tid_wakeup

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L827 | early return | NO | NO | ✅ | before any operation |
| L838–L845 (fqp==qp) | implicit fall‑through | **?** (first_qp may not take a ref) | YES (rvt_put_qp) | **❌ if GET=NO** | excess‑put warning at L844 |
| L838–L847 (fqp≠qp) | implicit fall‑through | **?** | **?** (tid_rdma_schedule_tid_wakeup may internally put) | unknown | |

Without the source of `first_qp()` we cannot confirm whether it increments the QP reference count.  
The kernel convention for names like `first_qp` is to return a borrowed pointer (no extra reference).  
If that is the case, calling `rvt_put_qp(fqp)` on the **same QP** path is an **excess put**—exactly the warning reported.  
The confidence is LOW because the semantics of the callees are unknown.

VERDICT: REAL_BUG  
CONFIDENCE: LOW
```
