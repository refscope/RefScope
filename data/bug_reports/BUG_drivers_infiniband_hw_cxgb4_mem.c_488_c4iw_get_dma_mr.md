# REAL BUG: drivers/infiniband/hw/cxgb4/mem.c:488 c4iw_get_dma_mr()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L? (success, return &mhp->ibmr) | success | YES | NO (ownership transferred) | ✅ | Reference stays with mhp, released later on mhp destruction. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L? (mhp alloc fails) | error (return ERR_PTR) | NO (before wr_waitp alloc) | N/A | ✅ | |
| L? (wr_waitp alloc fails, jumps to err_free_mhp) | error (goto err_free_mhp) | NO (wr_waitp == NULL) | N/A | ✅ | kfree(mhp) only, no put needed |
| L? (skb alloc fails, jumps to err_free_wr_wait) | error (goto err_free_wr_wait) | YES | YES (c4iw_put_wr_wait) | ✅ | |
| L? (write_tpt_entry fails, jumps to err_free_skb) | error (goto err_free_skb) | YES | YES (c4iw_put_wr_wait via fallthrough) | ✅ | |
| L? (finish_mem_reg fails, jumps to err_dereg_mem) | error (goto err_dereg_mem) | YES | YES (c4iw_put_wr_wait via fallthrough) | ❌ LIKELY LEAK (excess put) | dereg_mem called first; if it does a kref_put on wr_waitp, then subsequent c4iw_put_wr_wait is an extra put → refcount underflow. Warning suggests this double put. |
| L? (success, return &mhp->ibmr) | success | YES | NO (ownership transferred) | ✅ | Reference stays with mhp, released later on mhp destruction. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
dereg_mem likely consumes the wr_waitp reference, causing a double put on the finish_mem_reg error path; the subsequent c4iw_put_wr_wait in the fallthrough leads to a refcount excess put. Without dereg_mem source exact consumption cannot be confirmed, but the smatch warning points strongly to this path. [NEED_SOURCE] dereg_mem
```
