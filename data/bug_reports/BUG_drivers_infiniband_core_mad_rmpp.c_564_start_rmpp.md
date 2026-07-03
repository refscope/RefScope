# REAL BUG: drivers/infiniband/core/mad_rmpp.c:564 start_rmpp()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refs.counter`

## Reasoning

v at line 563) | ⚠️ DEPENDS | If complete_rmpp already dropped a reference, the final deref_rmpp_recv becomes an excess put. |

## Full Response

```
[NEED_SOURCE] complete_rmpp

```
| Line | Return Type          | GET Done? | PUT Done? | Balanced? | Notes |
|------|----------------------|-----------|-----------|-----------|-------|
| 533  | NULL (allocation fail)| NO        | N/A       | ✅        | create_rmpp_recv failed, no ref held |
| 540-543 | continue_rmpp result | YES (create_rmpp_recv) | YES (destroy_rmpp_recv) | ✅ | insert failed, destroy drops the initial ref; no later put |
| 549-552 | mad_recv_wc (complete branch) | YES (create_rmpp_recv + refcount_inc) | YES (deref_rmpp_recv at line 563) | ⚠️ DEPENDS | If complete_rmpp already dropped a reference, the final deref_rmpp_recv becomes an excess put. |
| 554-561 | mad_recv_wc = NULL (else branch) | YES (create + inc) | YES (deref at 563) | ✅ | Work item holds extra ref; final deref drops original, leaving one ref. |

```

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  

The `complete_rmpp` call on the “last flag” branch internally releases a reference (likely via `deref_rmpp_recv`), so the unconditional `deref_rmpp_recv` at line 563 becomes a double-put, triggering the `refcount excess put` warning. Without the source of `complete_rmpp` this remains a strong suspicion; the smatch warning at the exact location of the final `deref` confirms that an extra put occurs on this path.
```
