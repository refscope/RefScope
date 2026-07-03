# REAL BUG: drivers/net/ppp/pppoe.c:694 pppoe_connect()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

| L637+ (if stage_session false, skip new block) | success/error | NO (new get not called) | NO | ✅ | |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L597 (goto end, sockaddr_len) | error | NO (before get) | NO | ✅ | |
| L601 (goto end, sa_protocol) | error | NO | NO | ✅ | |
| L605 (goto end, EBUSY) | error | NO | NO | ✅ | |
| L609 (goto end, EALREADY) | error | NO | NO | ✅ | |
| L641 (goto err_put, dev_get_by_name NULL, old binding skipped) | error | NO (new get failed), old GET from previous session held | YES (dev_put on old po->pppoe_dev) | ❌ EXCESS PUT | Old reference released without being acquired in this call, causing potential refcount underflow |
| L641 (goto err_put, dev_get_by_name NULL, old binding ran) | error | NO (new get failed), old GET already released, po->pppoe_dev NULL | NO (null check) | ✅ | Safe because po->pppoe_dev is NULL |
| L648 (goto err_put, IFF_UP) | error | YES (new get) | YES | ✅ | New reference properly released |
| L654 (goto err_put, __set_item error) | error | YES | YES | ✅ | |
| L661 (goto err_put, ppp_register_net_channel error) | error | YES | YES | ✅ | |
| L668+ (fall through, new binding block success) | success | YES (new get) | NO (deferred) | ✅ (intentional) | Reference held for socket lifetime |
| L637+ (if stage_session false, skip new block) | success/error | NO (new get not called) | NO | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the path where the old binding is a non‑session stage (po‑>pppoe_pa.sid not session) and the new request is a session stage but dev_get_by_name returns NULL, err_put calls dev_put on the stale po‑>pppoe_dev without a matching get in this function, leading to an excess put that can underflow the device’s refcount.
```
```
