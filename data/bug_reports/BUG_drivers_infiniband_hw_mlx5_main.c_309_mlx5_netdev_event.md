# REAL BUG: drivers/infiniband/hw/mlx5/main.c:309 mlx5_netdev_event()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

| default case: break → put_ndev(L305) | fall‑through | NO | YES | ❌ EXCESS PUT | ib_ndev still NULL |

## Full Response

```
| Path / Line(s) | Return Type | GET (ib_ndev ref acquired?) | PUT (dev_put called?) | Balanced? | Notes |
|----------------|-------------|----------------------------|----------------------|-----------|-------|
| L217: !mdev | early return NOTIFY_DONE | NO | NO | ✅ | |
| NETDEV_REGISTER: is_rep, break → put_ndev (L305) | fall-through to L308 | NO | YES (dev_put(NULL)) | ❌ EXCESS PUT | ib_ndev still NULL |
| NETDEV_REGISTER: get_netdev(L225) returns non‑NULL, goto put_ndev(L228) | goto → L308 | YES | YES | ✅ | |
| NETDEV_REGISTER: get_netdev(L225) returns NULL, fall‑through, break → put_ndev(L305) | fall‑through | NO | YES (dev_put(NULL)) | ❌ EXCESS PUT | ib_ndev NULL, get failed |
| NETDEV_UNREGISTER: is_rep, break → put_ndev(L305) | fall‑through | NO | YES | ❌ EXCESS PUT | |
| NETDEV_UNREGISTER: get_netdev(L238) returns non‑NULL, goto put_ndev(L241) | goto | YES | YES | ✅ | |
| NETDEV_UNREGISTER: get_netdev(L238) returns NULL, goto put_ndev(L241) | goto | NO | YES | ❌ EXCESS PUT | |
| CHANGE/UP/DOWN: early return L250 | return NOTIFY_DONE | NO | NO | ✅ | |
| CHANGE/UP/DOWN: lag_ndev NULL, goto done(L306) → L308 | skip put_ndev | NO | NO | ✅ | |
| CHANGE/UP/DOWN: !roce L271 | return NOTIFY_DONE | NO | NO | ✅ | |
| CHANGE/UP/DOWN: get_netdev(L273) returns non‑NULL + goto put_ndev (L281/284/293) or fall‑through | goto/fall‑through | YES | YES | ✅ | |
| CHANGE/UP/DOWN: get_netdev(L273) returns NULL + goto put_ndev (L281/284/293) | goto | NO | YES | ❌ EXCESS PUT | |
| CHANGE/UP/DOWN: get_netdev(L273) returns NULL + fall‑through (send_event false) → put_ndev | fall‑through | NO | YES | ❌ EXCESS PUT | |
| default case: break → put_ndev(L305) | fall‑through | NO | YES | ❌ EXCESS PUT | ib_ndev still NULL |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`dev_put(ib_ndev)` at label `put_ndev` is reached with `ib_ndev == NULL` on multiple paths (is_rep breaks, get_netdev returning NULL, default), causing an excess put against `dev_refcnt`.
```
