# REAL BUG: net/ceph/osd_client.c:5473 get_reply()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

Pending confirmation from `ceph_msg_revoke_incoming` source, but the naming and code pattern point to a real double-put.

## Full Response

```
| Line | Return Type | GET Done? (ceph_msg_get) | PUT Done? (ceph_msg_put) | Balanced? | Notes |
|------|-------------|---------------------------|---------------------------|-----------|-------|
| L5418 (goto out_unlock_osdc) | error (osd unregistered) | NO (not reached) | NO (not reached) | ✅ | |
| L5427 (goto out_unlock_session) | error (req not found) | NO (not reached) | NO (not reached) | ✅ | |
| L5434‑... (front_len > prealloc, `ceph_msg_new` fails) | error (goto out_unlock_session) | NO (not reached) | NO (ceph_msg_put not called) | ✅ (revoke_incoming may put, but no double put) | |
| L5467‑5468 (front_len > prealloc, `ceph_msg_new` succeeds, then `ceph_msg_put(req->r_reply)`) | **excess put path** | YES (later, via `ceph_msg_get` on new `req->r_reply` at L5473+) | **YES (ceph_msg_put old reply)** | **❌ excess put** | If `ceph_msg_revoke_incoming` already puts, this second `ceph_msg_put` is an excess put. |
| L5477 (data_len > prealloc, `*skip=1`, goto out_unlock_session) | error (skip) | NO (not reached) | NO (ceph_msg_put not called) | ✅ | revoke_incoming possible but no double put. |
| L5482‑... (normal success) | success (m returned) | YES (`ceph_msg_get`) | NO (no explicit put on `req->r_reply`) | uncertain (depends on revoke) | GET+PUT pairing with the caller’s eventual put; revoke may have removed an incoming reference, balancing. |

[NEED_SOURCE] ceph_msg_revoke_incoming

**Explanation:**  
The warning flags an excess put on `ceph_msg_put(req->r_reply)` at line 5473. The only `ceph_msg_put` in this function is inside the `front_len > prealloc` replacement block. The sequence is:

1. `ceph_msg_revoke_incoming(req->r_reply)` is called unconditionally before the check.  
2. If the old reply needs replacement, we allocate a new `m` and then **put the old `req->r_reply` again**.  

If `ceph_msg_revoke_incoming` already dropped a reference (its name, “revoke incoming”, strongly suggests it puts the message to cancel an incoming reference), then the subsequent `ceph_msg_put` would be a **double-put** on the same message — exactly the “excess put” observed. The old reply does not yet have an extra incoming reference when `get_reply` runs (it is the function that obtains the reply buffer for the incoming message), so the revoke-incoming call is wrong, making the following put excessive. This is a classic refcounting bug.

Pending confirmation from `ceph_msg_revoke_incoming` source, but the naming and code pattern point to a real double-put.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`ceph_msg_revoke_incoming` likely calls `ceph_msg_put`, causing a double-put on `req->r_reply` when the front_len > prealloc replacement path is taken. The revoke should only happen when an incoming reference already exists, and must be paired with a single put (not a separate put afterwards).
```
