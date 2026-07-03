# REAL BUG: fs/nfsd/nfs4state.c:3336 create_client()

**Confidence**: HIGH | **Counter**: `clp->cl_nfsdfs.cl_ref.refcount.refs.counter`

## Reasoning

| L3336 | success (return clp) | YES | NO (ref transferred) | ✅ | Initial reference handed to caller |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3304 | error (alloc_client NULL) | NO | N/A | ✅ | No client allocated, no ref |
| L3309 | error (copy_cred fails) | NO (before kref_init) | YES (free_client) | ❌ EXCESS PUT | kref_init not called yet; free_client attempts kref_put on zero refcount → underflow |
| L3326 | error (!cl_nfsd_dentry) | YES (kref_init at L3312) | YES (free_client) | ✅ | Normal put of initial ref |
| L3331 | error (!cl_ra) | YES | YES | ✅ | |
| L3336 | success (return clp) | YES | NO (ref transferred) | ✅ | Initial reference handed to caller |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
free_client is called on the copy_cred error path (L3308) before kref_init (L3312), causing a kref_put on an uninitialized refcount (zero), i.e. an excess put that triggers the refcount underflow warning.
```
