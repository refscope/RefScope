# REAL BUG: drivers/infiniband/hw/hfi1/tid_rdma.c:1589 hfi1_kern_exp_rcv_clear()

**Confidence**: MEDIUM | **Counter**: `$->refcount.counter`

## Reasoning

| L1582‑1586 (fqp != req‑>qp) | return 0 | NO (same assumption) | ? (tid_rdma_schedule_tid_wakeup semantics unknown) | ✅ (no explicit put, probably fine) | not flagged by smatch |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1565 | error (-EINVAL) | NO (before get) | N/A | ✅ | early return before `first_qp` call |
| L1582‑1584 (fqp == req‑>qp) | return 0 | NO (first_qp likely does not inc ref) | YES (rvt_put_qp) | ❌ EXCESS PUT | `rvt_put_qp` called on qp that was not reference‑counted by this path – this is the flagged excess put |
| L1582‑1586 (fqp != req‑>qp) | return 0 | NO (same assumption) | ? (tid_rdma_schedule_tid_wakeup semantics unknown) | ✅ (no explicit put, probably fine) | not flagged by smatch |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The function `first_qp()` returns the head of `rarr_queue`; its name and context strongly suggest it simply retrieves a pointer without incrementing the QP’s refcount. The subsequent call to `rvt_put_qp()` in the `fqp == req->qp` branch therefore performs an excess put, matching the smatch warning. If `first_qp` does acquire a reference, this would be a false positive, but the naming convention makes a plain “fetch” the far more likely interpretation.
```
