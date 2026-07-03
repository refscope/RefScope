# REAL BUG: net/core/netdev-genl.c:1363 netdev_nl_queue_create_doit()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

*For dev, `netdev_get_by_index_lock` (a get wrapper, name implies reference acquisition) is called, but there is **no matching `netdev_put` or `dev_put` anywhere in the function**. All error and success paths after that call **leak the reference**, making the net_device permanently pinned.*

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1205 (GENL_REQ_ATTR_CHECK fail) | error | NO | N/A | ✅ | before any get |
| L1207 (queue type != RX) | error | NO | N/A | ✅ | |
| L1221 (nla_parse_nested fail) | error | NO | N/A | ✅ | |
| L1223 (NL_REQ_ATTR_CHECK fail) | error | NO | N/A | ✅ | |
| L1227 (capable fail) | error | NO | N/A | ✅ | |
| L1232 (nla_parse_nested fail) | error | NO | N/A | ✅ | |
| L1234 (lease NL_REQ_ATTR_CHECK fail) | error | NO | N/A | ✅ | |
| L1238 (lease queue type != RX) | error | NO | N/A | ✅ | |
| L1243 (genlmsg_new fail) | error | NO | N/A | ✅ | |
| L1247 (genlmsg_iput fail → goto err_genlmsg_free) | error | NO | N/A | ✅ | |
| L1255 (dev == NULL) → goto err_genlmsg_free | error | NO | N/A | ✅ | `netdev_get_by_index_lock` returned NULL, no ref held |
| L1260 (netdev_can_create_queue fail) → goto err_unlock_dev | error | YES (dev) | NO | ❌ LEAK | dev reference acquired by `netdev_get_by_index_lock`, never released; `err_unlock_dev` only unlocks |
| L1270 (get_net_ns_by_id fail) → goto err_unlock_dev | error | YES (dev) | NO | ❌ LEAK | same |
| L1275 (dev_lease NULL) → goto err_put_netns → err_unlock_dev | error | YES (dev) | NO | ❌ LEAK | dev ref still held |
| L1281 (can_lease_queue fail → netdev_put dev_lease → err_put_netns → err_unlock_dev) | error | YES (dev), YES (dev_lease) | dev_lease: YES, dev: NO | ❌ LEAK (dev) | dev_lease balance okay, dev ref leaked |
| L1284 (dev_lease NULL after netdev_put_lock) → goto err_put_netns → err_unlock_dev | error | YES (dev) | NO | ❌ LEAK | netdev_put_lock released dev_lease ref; dev ref still leaked |
| L1290 (queue_id_lease out of range → goto err_unlock_dev_lease ...) | error | YES (dev) | NO | ❌ LEAK | |
| L1294 (netdev_queue_busy → goto err_unlock_dev_lease ...) | error | YES (dev) | NO | ❌ LEAK | |
| L1318 (rxq->lease->dev != dev_lease → goto err_unlock_dev_lease ...) | error | YES (dev) | NO | ❌ LEAK | |
| L1325 (ndo_queue_create fail → goto err_unlock_dev_lease ...) | error | YES (dev) | NO | ❌ LEAK | |
| L1336 (success return) | success | YES (dev) | NO | ❌ LEAK | dev reference never dropped; no `netdev_put(dev)` anywhere |

*For dev_lease, the reference lifecycle is balanced (one get via `netdev_get_by_index`, consumed by `netdev_put_lock` or explicitly put on the early error path).*

*For dev, `netdev_get_by_index_lock` (a get wrapper, name implies reference acquisition) is called, but there is **no matching `netdev_put` or `dev_put` anywhere in the function**. All error and success paths after that call **leak the reference**, making the net_device permanently pinned.*

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`netdev_get_by_index_lock` acquires a reference on `dev`, but the function never releases it — a clear reference leak in every path after that call. The `netdev_unlock` function only unlocks the device's mutex, it does not drop the reference count. The reported “excess put” 
```
