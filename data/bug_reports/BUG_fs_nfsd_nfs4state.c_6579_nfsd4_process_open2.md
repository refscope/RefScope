# REAL BUG: fs/nfsd/nfs4state.c:6579 nfsd4_process_open2()

**Confidence**: HIGH | **Counter**: `$->st_stid.sc_count.refs.counter`

## Reasoning

| normal success, new_stp true, no xor | YES | YES (nfs4_put_stid) | ✅ | |

## Full Response

```
| Path | GET Done? | PUT Done? | Balanced? | Notes |
|------|-----------|-----------|-----------|-------|
| return nfserr_jukebox (fp NULL) | NO | N/A | ✅ | |
| goto out from nfs4_check_deleg fail | NO | N/A | ✅ | |
| goto out from deleg mismatch | NO | N/A | ✅ | |
| goto out from deleg_cur early | NO | N/A | ✅ | |
| goto out from init_open_stateid fail | NO | N/A | ✅ | stp set to NULL |
| goto out from nfs4_upgrade_open fail | YES (nfsd4_find_and_lock_existing_open) | YES (nfs4_put_stid at out) | ✅ | |
| goto out after nfs4_get_vfs_file fail (release_open_stateid called) | YES (init_open_stateid) | YES (release_open_stateid) + extra nfs4_put_stid at out | ❌ DOUBLE‑PUT | release_open_stateid decrements ref, then out does it again; stp not nullified |
| normal flow, new_stp && open_xor_delegation true (release_open_stateid then out) | YES (init_open_stateid) | YES (release_open_stateid) + extra nfs4_put_stid at out | ❌ DOUBLE‑PUT | same double‑put because stp still non‑NULL |
| normal success, new_stp false (upgrade) | YES | YES (nfs4_put_stid) | ✅ | |
| normal success, new_stp true, no xor | YES | YES (nfs4_put_stid) | ✅ | |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`release_open_stateid()` already puts the reference, but the caller does not nullify `stp`, causing a second `nfs4_put_stid()` at the `out:` label – double‑put on `st_stid.sc_count` refcounter.
```
