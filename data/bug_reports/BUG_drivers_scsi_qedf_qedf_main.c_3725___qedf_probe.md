# REAL BUG: drivers/scsi/qedf/qedf_main.c:3725 __qedf_probe()

**Confidence**: HIGH | **Counter**: `$->tagset_refcnt.refcount.refs.counter`

## Reasoning

- Thus in recovery mode, these paths execute `scsi_remove_host` without a prior `scsi_add_host`, causing a **put without matching get** on the host’s `tagset_refcnt` → inconsistent refcounting.

## Full Response

```
| Line | Return Type | GET Done? (scsi_add_host) | PUT Done? (scsi_remove_host) | Balanced? | Notes |
|------|-------------|---------------------------|------------------------------|-----------|-------|
| L3310 (goto err0) | error | NO (lport alloc fail) | NO | ✅ | host not allocated |
| L3336 (goto err1) | error | NO (before scsi_add_host) | NO | ✅ | io_mempool NULL |
| L3367 (goto err1) | error (common probe fail) | NO | NO | ✅ | |
| L3386 (goto err1) | error (fill_dev_info fail) | NO | NO | ✅ | |
| L3402 (goto err2) | error (set_fcoe_pf_param fail) | NO | NO | ✅ | |
| L3413 (goto err2) | error (2nd fill_dev_info fail) | NO | NO | ✅ | |
| L3419 (goto err2) | error (devlink register fail) | NO | NO | ✅ | |
| L3430 (goto err2) | error (prepare_sb fail) | NO | NO | ✅ | |
| L3442 (goto err2) | error (slowpath_start fail) | NO | NO | ✅ | |
| L3450 (goto err3) | error (setup_int fail) | NO | NO | ✅ | |
| L3455 (goto err4) | error (start fail) | NO | NO | ✅ | |
| L3482 (goto err5) | error (cmd_mgr alloc fail) | NO | NO | ✅ | |
| L3495 (goto err6) | error (scsi_add_host fail) | NO (rc != 0) | NO (jumps to err6, no remove) | ✅ | scsi_add_host failed, no ref taken |
| L3517 (goto err7) | error (ll2_recv_wq fail) | `scsi_add_host` succeeded in non-recovery → YES; in recovery → NO | YES (err7 calls `scsi_remove_host`) | ❌ in RECOVERY: PUT without GET | ll2_recv_wq fail can occur in both modes, err7 removes host unconditionally |
| L3525 (goto err7) | error (ll2 start fail) | same | YES | ❌ in RECOVERY | |
| L3537 (goto err7) | error (lport_setup fail) | YES (lport_setup only called in non-recovery, scsi_add_host succeeded before) | YES | ✅ | lport_setup skipped in recovery, never reached |
| L3546 (goto err7) | error (timer_work_queue fail) | same as L3517 | YES | ❌ in RECOVERY | timer_work_queue alloc fail can occur in either mode |
| L3645 (return 0) | success | YES (non-recovery), NO (recovery) | NO (owned by device, released in remove) | ✅ | lifetime reference |

**Critical findings**:  
- In **recovery mode** (`mode == QEDF_MODE_RECOVERY`), `scsi_add_host` is **never called**, so no tagset reference is taken.  
- Error paths after this point (ll2_recv_wq alloc, ll2 start, timer_work_queue alloc) all jump to `err7`, which **unconditionally** calls `scsi_remove_host`.  
- Thus in recovery mode, these paths execute `scsi_remove_host` without a prior `scsi_add_host`, causing a **put without matching get** on the host’s `tagset_refcnt` → inconsistent refcounting.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
In recovery mode `err7` calls `scsi_remove_host` without a matching `scsi_add_host`, causing a refcount imbalance on the SCSI host’s tagset refcnt.
```
