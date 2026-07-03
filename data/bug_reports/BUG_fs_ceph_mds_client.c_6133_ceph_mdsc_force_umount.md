# REAL BUG: fs/ceph/mds_client.c:6133 ceph_mdsc_force_umount()

**Confidence**: HIGH | **Counter**: `session->s_ref.refs.counter`

## Reasoning

, s_state == REJECTED** | fall‑through to end of loop | **YES** | **NO – two puts** | **❌ EXCESS** | __ceph_lookup_mds_session gives a reference; then __unregister_session() calls ceph_put_mds_session (first put); later L6127 does ceph_put_mds_session (second put) → double put, refcount overflow |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L6111 (session=NULL) | continue loop | NO | N/A | ✅ | No session found, no get |
| L6111 non‑NULL, s_state != REJECTED | fall‑through to end of loop | YES (from __ceph_lookup_mds_session) | YES – one put at L6127 | ✅ | One get, one put |
| **L6111 non‑NULL, s_state == REJECTED** | fall‑through to end of loop | **YES** | **NO – two puts** | **❌ EXCESS** | __ceph_lookup_mds_session gives a reference; then __unregister_session() calls ceph_put_mds_session (first put); later L6127 does ceph_put_mds_session (second put) → double put, refcount overflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
__ceph_lookup_mds_session acquires a reference; if session is in CEPH_MDS_SESSION_REJECTED state, __unregister_session already drops that reference, yet the loop body unconditionally calls ceph_put_mds_session again, causing an excess put.
```
