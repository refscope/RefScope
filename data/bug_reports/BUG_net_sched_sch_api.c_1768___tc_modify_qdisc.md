# REAL BUG: net/sched/sch_api.c:1768 __tc_modify_qdisc()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

erence with `qdisc_put(q)`. The code fails to do this in the `return 0` path. The error path correctly calls `qdisc_put(q)`, so the error path is balanced. No ownership transfer or deferred cleanup mechanism applies to this temporary reference. Therefore the success path leaks one reference count.

## Full Response

```
## Path Table

| Line (approx.) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|----------------|-------------|-----------|-----------|-----------|-------|
| L1601          | error (-ENOENT) | NO (lookup before any get) | N/A | ✅ | p not found |
| L1606          | error (-EOPNOTSUPP) | NO | N/A | ✅ | p is ingress, no ref taken |
| L1610          | error (PTR_ERR(q)) | NO (qdisc_leaf may return error, no ref held) | N/A | ✅ | IS_ERR guard |
| L1627          | error (-EEXIST) | NO | N/A | ✅ | early return, no get |
| L1631          | error (-EINVAL) | NO | N/A | ✅ | |
| L1634          | goto create_n_graft | NO (if q is NULL, no ref held) | N/A | ✅ | will later create new qdisc, balance handled by create+graft path |
| L1639          | error (-EINVAL) | NO | N/A | ✅ | |
| L1643          | error (-EEXIST) | NO | N/A | ✅ | |
| L1648          | error (-EINVAL) | NO | N/A | ✅ | |
| L1657          | error (-EINVAL) | NO | N/A | ✅ | |
| L1661          | error (-ELOOP) | NO | N/A | ✅ | |
| L1665          | error (-EINVAL) | NO | N/A | ✅ | |
| L1668          | **goto graft** after `qdisc_refcount_inc(q)` | **YES** (explicit inc) | **NO** | ❌ **LEAK** | Success path from graft label returns 0 without put |
| L1668 → graft success | return 0 | **YES** | **NO** | ❌ **LEAK** | `qdisc_refcount_inc` reference never released on success |
| L1668 → graft failure | return err | **YES** | **YES** (qdisc_put) | ✅ | error path puts reference |
| L1677          | error (-ENOENT) | NO (no get, q is NULL) | N/A | ✅ | q not found |
| L1681          | error (-EEXIST) | NO | N/A | ✅ | |
| L1685          | error (-EINVAL) | NO | N/A | ✅ | |
| L1688          | return err (after qdisc_change) | NO (no refinc, only lookup) | N/A | ✅ | change path does not acquire ref |
| L1694          | error (-ENOENT) | NO | N/A | ✅ | create_n_graft path, no get yet |
| L1695          | return err (if q==NULL after create) | depends on create: if q non-NULL then qdisc_create gave refcount=1 | N/A | ✅ | q is NULL, so no get |
| L1695 → graft failure | return err | YES (from create) | YES (qdisc_put) | ✅ | owned by caller, put on error |
| L1695 → graft success | return 0 | YES (from create) | NO (ownership transferred) | ✅ | create provides ref, graft consumes it |

## Verdict Reasoning

The leak is on the **success path** after `qdisc_refcount_inc(q)` → `goto graft`. The function explicitly takes a reference on an existing qdisc via `qdisc_refcount_inc` to protect the object during the graft operation. If the graft succeeds, the caller must release this temporary reference with `qdisc_put(q)`. The code fails to do this in the `return 0` path. The error path correctly calls `qdisc_put(q)`, so the error path is balanced. No ownership transfer or deferred cleanup mechanism applies to this temporary reference. Therefore the success path leaks one reference count.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
