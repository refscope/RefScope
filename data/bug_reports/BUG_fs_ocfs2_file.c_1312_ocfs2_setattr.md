# REAL BUG: fs/ocfs2/file.c:1312 ocfs2_setattr()

**Confidence**: HIGH | **Counter**: `$->dq_count.counter`

## Reasoning

| **dqgets succeed, __dquot_transfer succeeds (status==0), fall‑through → bail_commit → bail** | **YES** | **YES (unwanted)** | **❌ EXCESS PUT** | After successful transfer, ownership moved to inode; the dqput at bail is an extra decrement |

## Full Response

```
```
| Path Description                                     | GET Done? | PUT Done? | Balanced?          | Notes                                                                                           |
|------------------------------------------------------|-----------|-----------|--------------------|-------------------------------------------------------------------------------------------------|
| Early return (L1131: !OCFS2_VALID_ATTRS)             | NO        | N/A       | N/A (safe)         | No dqget called yet                                                                             |
| setattr_prepare fail (L1134)                         | NO        | N/A       | N/A (safe)         |                                                                                                 |
| dquot_initialize fail (L1139)                        | NO        | N/A       | N/A (safe)         |                                                                                                 |
| emergency_state goto bail (L1119 → bail)             | NO        | No-op     | ✅ (safe)          | transfer_to[] is zero, dqput(NULL) no-op                                                        |
| rw_lock fail goto bail_unlock_rw → bail              | NO        | No-op     | ✅ (safe)          |                                                                                                 |
| size_change/inode error goto bail_unlock → bail      | NO        | No-op     | ✅ (safe)          |                                                                                                 |
| dqget for USRQUOTA returns ERR_PTR, set NULL → bail_unlock → bail | NO (IS_ERR) | No-op     | ✅ (safe)          | dqput(NULL)                                                                                     |
| dqget for GRPQUOTA returns ERR_PTR, set NULL → bail_unlock → bail | NO (IS_ERR) | No-op     | ✅ (safe)          |                                                                                                 |
| dqgets succeed, handle alloc fails → bail_unlock_alloc → bail | YES       | YES       | ✅ (safe)          | dqput done before transfer                                                                      |
| dqgets succeed, __dquot_transfer fails → bail_commit → bail      | YES       | YES       | ✅ (safe)          | transfer did not occur, caller still owns refs                                                  |
| **dqgets succeed, __dquot_transfer succeeds (status==0), fall‑through → bail_commit → bail** | **YES** | **YES (unwanted)** | **❌ EXCESS PUT** | After successful transfer, ownership moved to inode; the dqput at bail is an extra decrement |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After a successful __dquot_transfer (L1260), the dqput loop at L1312 releases references that were already consumed, causing an excess put (refcount underflow).```
```
