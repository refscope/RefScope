# REAL BUG: drivers/net/wireguard/netlink.c:470 set_peer()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L439 | success (normal end after lookup) | YES (1 get) | YES (wg_peer_put) | ✅ | balanced |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L360 | goto out (invalid key) | NO (peer=NULL) | N/A (wg_peer_put(NULL) no-op) | ✅ | peer never set |
| L369 | goto out (flags on not-found peer) | NO (peer=NULL) | N/A | ✅ | peer=NULL from lookup failure |
| L377 | goto out (static identity match) | NO (peer=NULL) | N/A | ✅ | peer=NULL before creation |
| L383 | goto out (creation error) | NO (peer=NULL after IS_ERR) | N/A | ✅ | peer set to NULL, no get held |
| L389 | goto out (remove_me after creation) | YES (2 gets: wg_peer_create+wg_peer_get) | YES (wg_peer_put) | ❌ LEAK | 2 gets, 1 put (wg_peer_remove may not release ref) |
| L421 | goto out (allowedips nla_parse_nested error after creation) | YES (2 gets) | YES (wg_peer_put) | ❌ LEAK | 2 gets, 1 put |
| L424 | goto out (set_allowedip error after creation) | YES (2 gets) | YES (wg_peer_put) | ❌ LEAK | 2 gets, 1 put |
| L439 | success (normal end after creation) | YES (2 gets) | YES (wg_peer_put) | ❌ LEAK | 2 gets, 1 put; peer not returned or stored in this function |
| L389 | goto out (remove_me after lookup) | YES (1 get from lookup) | YES (wg_peer_put) | ✅ | 1 get, 1 put |
| L421 | goto out (allowedips error after lookup) | YES (1 get) | YES (wg_peer_put) | ✅ | balanced |
| L424 | goto out (set_allowedip error after lookup) | YES (1 get) | YES (wg_peer_put) | ✅ | balanced |
| L439 | success (normal end after lookup) | YES (1 get) | YES (wg_peer_put) | ✅ | balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the peer creation path, `wg_peer_create` initialises refcount to 1 and `wg_peer_get` increments it to 2, but only one `wg_peer_put` is performed at the `out:` label, leaving the new peer with a reference count of 1 without transferring ownership inside this function.
```
