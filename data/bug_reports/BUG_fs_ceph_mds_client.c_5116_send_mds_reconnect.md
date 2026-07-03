# REAL BUG: fs/ceph/mds_client.c:5116 send_mds_reconnect()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

**⚠️ Warning line 5116** is the `ceph_msg_put(reply)` call, which is correctly paired with the `ceph_msg_new2` get on all the error paths. The actual refcount bug is the missing `ceph_msg_put` on the successful path after `ceph_con_send`, resulting in a reference leak.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4955 (via `fail_nopagelist`) | error return | NO (before get) | N/A | ✅ | pagelist alloc failed, no get |
| L4960 (via `fail_nomsg`) | error return | NO (get failed) | N/A | ✅ | `ceph_msg_new2` returned NULL, no ref held |
| L~5138 (success path, after `ceph_con_send`) | return | YES | NO | ❌ **LEAK** | `ceph_msg_new2` gave a ref; `ceph_con_send` takes its own ref, caller’s ref is leaked |
| L5027 (via `fail_clear_cap_reconnect` → `fail`) | error return | YES | YES | ✅ | `ceph_msg_put` at `fail` label |
| L5039 (`err < 0` → `fail`) | error return | YES | YES | ✅ | `ceph_msg_put` at `fail` |
| L5060 (ENOSPC → `fail`) | error return | YES | YES | ✅ | `ceph_msg_put` at `fail` |
| L5064 (`send_reconnect_partial` fail → `fail`) | error return | YES | YES | ✅ | `ceph_msg_put` at `fail` |
| L5069 (`encode_snap_realms` fail → `fail`) | error return | YES | YES | ✅ | `ceph_msg_put` at `fail` |
| L5073 (`ceph_pagelist_encode_8` fail → `fail`) | error return | YES | YES | ✅ | `ceph_msg_put` at `fail` |

**⚠️ Warning line 5116** is the `ceph_msg_put(reply)` call, which is correctly paired with the `ceph_msg_new2` get on all the error paths. The actual refcount bug is the missing `ceph_msg_put` on the successful path after `ceph_con_send`, resulting in a reference leak.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
reply from ceph_msg_new2 is never released with ceph_msg_put on the success path, causing a reference leak (missing put).
```
