# REAL BUG: fs/nfsd/nfs4state.c:7292 nfsd4_lookup_stateid()

**Confidence**: MEDIUM | **Counter**: `$->sc_count.refs.counter`

## Reasoning

- Without the source of `nfsd40_drop_revoked_stid`, we cannot be 100% certain, but the naming convention and the fact that the warning is “refcount excess put” at that location (likely the explicit put) strongly indicate a double-put.

## Full Response

```
| Line (in snippet) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|-------------------|-------------|-----------|-----------|-----------|-------|
| L10 (ZERO_STATEID/ONE/CLOSE early return) | error | NO (before get) | N/A | ✅ | |
| L14 (stale_clientid, session) | error | NO (before get) | N/A | ✅ | |
| L16 (stale_clientid, no session) | error | NO (before get) | N/A | ✅ | |
| L18 (other set_client error) | error | NO (before get) | N/A | ✅ | |
| L21 (find_stateid_by_type returns NULL) | error | NO (get failed) | N/A | ✅ | |
| L24 (SC_STATUS_REVOKED, !return_revoked) | error | YES | YES (explicit nfs4_put_stid) | ✅ | Get balanced by put |
| L29 (SC_STATUS_ADMIN_REVOKED) | error | YES | YES (explicit nfs4_put_stid) | ⚠️ Potential double-put | **nfsd40_drop_revoked_stid** may already release the reference; subsequent `nfs4_put_stid` would be excess |
| L32 (success, *s = stid) | success | YES | NO (ownership transfer) | ✅ | Reference passed to caller |

[NEED_SOURCE] nfsd40_drop_revoked_stid
The `nfsd40_drop_revoked_stid` function is called before an explicit `nfs4_put_stid` in the ADMIN_REVOKED error path. Its name strongly suggests it removes the stateid from tracking and likely releases the reference held by the caller. If it internally calls `nfs4_put_stid` (or equivalent), then the explicit put at line L29 becomes an **excess put**, exactly matching the warning on `sc_count.refs.counter`.

**Analysis:**
- In the ADMIN_REVOKED branch, the code first calls `nfsd40_drop_revoked_stid(cstate->clp, stateid)` and then calls `nfs4_put_stid(stid)`.
- The typical pattern for “drop” helpers in the NFSD state management is that they handle the removal of the stateid from internal lists/IDR and also release the **last** reference (or the reference that was being held for tracking). If that is the case here, then the subsequent `nfs4_put_stid` would be a double-free / refcount underflow.
- Without the source of `nfsd40_drop_revoked_stid`, we cannot be 100% certain, but the naming convention and the fact that the warning is “refcount excess put” at that location (likely the explicit put) strongly indicate a double-put.

**VERDICT: REAL_BUG**
**CONFIDENCE: MEDIUM**

The ADMIN_REVOKED error path in `nfsd4_lookup_stateid` likely causes a double-put on `stid->sc_count` because `nfsd40_drop_revoked_stid` already releases the reference, and the function then attempts an extra `nfs4_put_stid`.
```
