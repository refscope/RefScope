# REAL BUG: drivers/infiniband/sw/rxe/rxe_mw.c:160 rxe_do_bind_mw()

**Confidence**: HIGH | **Counter**: `$->ref_cnt.refcount.refs.counter`

## Reasoning

| L161 (end of function) | void return | all gets done or skipped based on conditions | no puts for new gets | Imbalance carried to cleanup: any failed get leads to excess put later | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L146 (mw->mr != NULL) | continuation | `rxe_put(mw->mr)` executed (put, not get) | YES (put old mr) | Balanced iff old get correct | Releases previous mr reference; not in question |
| L154 (mw->length != 0) | continuation | `rxe_get(mr)` CONDITIONAL (__rxe_get only incs on success, returns zero on failure). Return value NOT checked. | NO put for mr in this function | GET=YES if __rxe_get succeeds, NO if it fails. On failure, mw->mr is still set → later unconditional `rxe_put(mw->mr)` will be excess | ❌ Missing return check |
| L158 (mw->ibmw.type == IB_MW_TYPE_2) | continuation | `rxe_get(qp)` CONDITIONAL, return value NOT checked. | NO put for qp in this function | GET=YES on success, NO on failure. On failure, mw->qp is set → later unconditional `rxe_put(mw->qp)` will be excess | ❌ Missing return check |
| L161 (end of function) | void return | all gets done or skipped based on conditions | no puts for new gets | Imbalance carried to cleanup: any failed get leads to excess put later | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rxe_get` is a conditional wrapper (`__rxe_get` → `kref_get_unless_zero`) whose return value is ignored at lines 154 and 158; the pointer is stored regardless, so a failed get leads to a later unconditional `rxe_put` on a refcount that was never taken, causing the excess put detected at line 160.
```
