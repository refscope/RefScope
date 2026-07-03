# REAL BUG: drivers/scsi/libiscsi.c:2497 iscsi_eh_abort()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L2445 (goto failed) | FAILED | YES | YES | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2368 | SUCCESS (early: no task) | NO | NO | ✅ | Before any get |
| L2376 | FAILED (session not connected) | NO | NO | ✅ | |
| L2386 | SUCCESS (task disappeared) | NO | NO | ✅ | |
| L2406 (goto success) | SUCCESS (via success_unlocked) | YES | YES (iscsi_put_task) + **extra** from fail_scsi_task | ❌ **excess put** | fail_scsi_task at L2405 releases ref, then iscsi_put_task at L2452 double-puts |
| L2410 (goto failed) | FAILED (via failed_unlocked) | YES | YES (cond: !running_aborted_task)  | ✅ | running_aborted_task not set → one put |
| L2417 (goto failed) | FAILED | YES | YES | ✅ | |
| L2429 (goto success_unlocked) | SUCCESS | YES | YES (iscsi_put_task) + **extra** from fail_scsi_task | ❌ **excess put** | fail_scsi_task at L2424 releases ref, then iscsi_put_task at L2452 |
| L2434 (goto failed_unlocked) | FAILED | YES | NO (running_aborted_task set) | ❌ leak (not excess) | Separate bug; ref held for conn cleanup |
| L2440 (goto success) | SUCCESS | YES | YES | ✅ | No fail_scsi_task |
| L2445 (goto failed) | FAILED | YES | YES | ✅ | |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**
`fail_scsi_task` internally releases the task’s reference, causing subsequent `iscsi_put_task` to hit an already-dropped refcount (excess put) on the ISCSI_TASK_PENDING and TMF_SUCCESS paths.
```
