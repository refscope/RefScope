# REAL BUG: fs/nfsd/nfs4state.c:8244 find_or_create_lock_stateid()

**Confidence**: HIGH | **Counter**: `$->sc_count.refs.counter`

## Reasoning

| L8242 (lst not found, alloc ok, lst != openlockstateid(ns)) | success, lst | YES (ns alloc get) | YES (nfs4_put_stid(ns)) | ❌ EXCESS PUT | init_lock_stateid already put ns, double put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L8231 (goto out) | success, lst | YES (lst from find_lock_stateid) | NO | ✅ | ref passed to caller |
| L8236 (ns == NULL) | error NULL | NO | N/A | ✅ | alloc failed |
| L8231 (lst found, lock fails, ns alloc fails) | error NULL (via alloc fail) | YES (lst get then put) | YES (put lst) | ✅ | lst balanced |
| L8231 (lst found, lock fails, alloc ok, lst == openlockstateid(ns)) | success, lst | YES (lst put, ns alloc get) | NO (ns) | ✅ | ns ref kept |
| L8242 (lst found, lock fails, alloc ok, lst != openlockstateid(ns)) | success, lst | YES (lst put, ns alloc get) | YES (nfs4_put_stid(ns)) | ❌ EXCESS PUT | init_lock_stateid already put ns, double put |
| L8231 (lst not found, alloc ok, lst == openlockstateid(ns)) | success, lst | YES (ns alloc get) | NO | ✅ | ns ref kept |
| L8242 (lst not found, alloc ok, lst != openlockstateid(ns)) | success, lst | YES (ns alloc get) | YES (nfs4_put_stid(ns)) | ❌ EXCESS PUT | init_lock_stateid already put ns, double put |

**PRE-VERDICT Checklist**:
- Ownership transfer? No, init_lock_stateid handles ownership.
- Unconditional GET? nfs4_alloc_stid is unconditional, so every path after it must put unless transferred.
- Error paths in probe? N/A.
- goto out between get and put? No, but the else put happens after the get; the issue is double put, not missing put.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`init_lock_stateid` releases the new stateid when it returns a different pointer; the caller's `nfs4_put_stid(ns)` in the else branch causes a double-put (excess put).
```
