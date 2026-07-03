# REAL BUG: net/ceph/messenger_v2.c:3351 populate_out_iter()

**Confidence**: HIGH | **Counter**: `$->out_msg->kref.refcount.refs.counter`

## Reasoning

| L3371 (nothing_pending) | return 0 | NO | N/A | ✅ | clean return, no message acquired |

## Full Response

```
| Line | Return Type | GET Done? (ceph_con_get_out_msg) | PUT Done? (finish_message) | Balanced? | Notes |
|------|-------------|----------------------------------|----------------------------|-----------|-------|
| L3288 (goto nothing_pending → L3371) | goto | NO (before get) | N/A | ✅ | state != OPEN → early return |
| L3330 (default: return -EINVAL) | return -EINVAL | NO (before any get) | N/A | ✅ | switch default case |
| L3345 (prepare_keepalive2 fail) | return ret | NO (get not called) | N/A | ✅ | keepalive path |
| **L3351 (prepare_message fail)** | **return ret** | **YES** (ceph_con_get_out_msg returned non‑NULL) | **NO** | **❌ LEAK** | msg ref obtained but never released |
| L3357 (prepare_ack fail) | return ret | NO | N/A | ✅ | ack path |
| L3359 (else → goto nothing_pending → L3371) | goto → return 0 | NO | N/A | ✅ | no pending work |
| L3364 (populated: WARN_ON return) | return -ENODATA | NO (reachable only from switch cases using con->out_msg, not from the get under audit) | N/A | ✅ | different get (not ceph_con_get_out_msg) |
| L3367 (populated: success) | return 1 | NO (same as above) | N/A | ✅ | success path for queued messages |
| L3371 (nothing_pending) | return 0 | NO | N/A | ✅ | clean return, no message acquired |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ceph_con_get_out_msg` obtains a reference (ceph_msg_get). On the error return at line 3351, the function returns without calling `finish_message` (which would perform ceph_msg_put), leaking the reference.
```
