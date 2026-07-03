# REAL BUG: fs/nfsd/nfs4state.c:8534 nfsd4_lock()

**Confidence**: MEDIUM | **Counter**: `$->nbl_kref.refcount.refs.counter`

## Reasoning

eturns `FILE_LOCK_DEFERRED`: `kref_put` + `nbl=NULL` → out | NULL after put | Conditional, but list ref dropped, nbl set NULL | No (skip free)               | ✅?        | lists still hold their own ref; no excess put here                                                                          |

## Full Response

```
| Path   | Description                                                       | nbl state   | GET Done? (find_or_allocate_block) | PUT Done? (free_blocked_lock) | Balanced? | Notes                                                                                                                      |
|--------|-------------------------------------------------------------------|-------------|-----------------------------------|------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------------|
| L8317  | `check_lock_length` fails → return                                | NULL        | N/A                               | N/A                          | ✅         | no nbl involvement                                                                                                         |
| L8322  | `fh_verify` fails → return                                        | NULL        | N/A                               | N/A                          | ✅         |                                                                                                                            |
| L8325  | `exportfs_cannot_lock` → goto out                                 | NULL        | N/A                               | No (skipped)                 | ✅         |                                                                                                                            |
| L8341  | `nfs4_preprocess_confirmed_seqid_op` fails → goto out              | NULL        | N/A                               | No                           | ✅         |                                                                                                                            |
| L8347  | `!same_clid` → goto out                                            | NULL        | N/A                               | No                           | ✅         |                                                                                                                            |
| L8353  | `lookup_or_create_lock_state` (or seqid) fails → goto out           | NULL        | N/A                               | No                           | ✅         |                                                                                                                            |
| L8362  | `nfs4_check_openmode` fails → goto out                             | NULL        | N/A                               | No                           | ✅         |                                                                                                                            |
| L8367  | `locks_in_grace` check fails → goto out                            | NULL        | N/A                               | No                           | ✅         |                                                                                                                            |
| L8369  | `!locks_in_
```
