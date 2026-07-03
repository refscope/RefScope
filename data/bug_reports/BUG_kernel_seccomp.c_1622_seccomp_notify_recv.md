# REAL BUG: kernel/seccomp.c:1622 seccomp_notify_recv()

**Confidence**: MEDIUM | **Counter**: `filter->notif->requests.counter`

## Reasoning

| L1598–L1615 copy_to_user fails, knotif not found | error (-EFAULT) | NO | **YES** | ⚠️ **POTENTIAL LEAK** | recv_wait_event succeeded (put) but notification disappeared before re-add → no get, underflow. |

## Full Response

```
| Line | Return Type | GET Done? (atomic_inc) | PUT Done? (recv_wait_event) | Balanced? | Notes |
|------|-------------|------------------------|----------------------------|-----------|-------|
| L1562 (ret < 0) | error | NO | NO (before call) | ✅ | check_zeroed_user failed, recv_wait_event not called |
| L1564 (ret == 0) | error | NO | NO (before call) | ✅ | invalid user buffer, no recv_wait_event |
| L1570 (recv_ret < 0) | error | NO | UNKNOWN (depends on recv_wait_event internals) | ⚠️ | If recv_wait_event does a put even on error, then PUT=YES → leak. Assumed safe but uncertain. |
| L1585 (goto out, knotif==NULL) | error (-ENOENT) | NO | **YES** (recv_wait_event succeeded, likely consumed a request) | ❌ **LEAK** | recv_wait_event returned 0 → put performed. knotif not found → no atomic_inc. Net excess put, refcount may underflow. |
| L1594…ret=0, copy_to_user succeeds | success (0) | NO | **YES** | ✅ (intended consumption) | Notification consumed, no get needed |
| L1598–L1615 copy_to_user fails, knotif found | error (-EFAULT) | **YES** (L1611 atomic_inc) | **YES** | ✅ | put re-added, refcount preserved |
| L1598–L1615 copy_to_user fails, knotif not found | error (-EFAULT) | NO | **YES** | ⚠️ **POTENTIAL LEAK** | recv_wait_event succeeded (put) but notification disappeared before re-add → no get, underflow. |

[NEED_SOURCE] recv_wait_event

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The missing notification path (knotif==NULL after recv_wait_event) returns -ENOENT without re-incrementing the requests counter, so a successful recv_wait_event (which likely decrements requests) leaves an unmatched put. This can cause an underflow when a notification is stolen by a concurrent reader.
```
