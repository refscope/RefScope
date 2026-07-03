# REAL BUG: net/bluetooth/iso.c:312 __iso_chan_add()

**Confidence**: MEDIUM | **Counter**: `sk->sk_peer_pid->count.refs.counter`

## Reasoning

| L312 | return 0 (after setting, parent non-NULL) | NO (no get_pid in __iso_chan_add) | YES (bt_accept_enqueue includes unconditional put_pid per contract) | ❌ EXCESS PUT | put_pid without prior get_pid — refcount underflow |

## Full Response

```
| Line | Return Type | GET Done? (get_pid on sk_peer_pid) | PUT Done? (put_pid on sk_peer_pid) | Balanced? | Notes |
|------|-------------|-------------------------------------|-------------------------------------|-----------|-------|
| L298 | return 0 (already set) | NO | NO | ✅ N/A | bt_accept_enqueue not called |
| L302 | return -EBUSY (conn->sk set) | NO | NO | ✅ N/A | bt_accept_enqueue not called |
| L312 | return 0 (after setting, parent non-NULL) | NO (no get_pid in __iso_chan_add) | YES (bt_accept_enqueue includes unconditional put_pid per contract) | ❌ EXCESS PUT | put_pid without prior get_pid — refcount underflow |

---
VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`bt_accept_enqueue` unconditionally performs `put_pid` (per contract) but `__iso_chan_add` contains no corresponding `get_pid` for `sk->sk_peer_pid`; the path at L312 where `parent` is non‑NULL therefore executes an unpaired put, causing the reported excess‑put on the child socket’s peer pid refcount.
```
