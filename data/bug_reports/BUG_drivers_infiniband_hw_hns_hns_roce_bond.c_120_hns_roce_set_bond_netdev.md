# REAL BUG: drivers/infiniband/hw/hns/hns_roce_bond.c:120 hns_roce_set_bond_netdev()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

set_netdev success) | return 0 | YES (ib_device_get_netdev) but **released by ib_device_set_netdev** per contract | YES (dev_put) → **extra release** | ❌ BUG: double put | `ib_device_set_netdev` already calls `netdev_put(old)`; the later `dev_put(old_dev)` over‑releases the refcount (underflow). |

## Full Response

```
| Line | Return Type | GET Done? (old_dev) | PUT Done? (old_dev at out) | Balanced? | Notes |
|------|-------------|----------------------|----------------------------|-----------|-------|
| L103 (goto out, old_dev == active_dev) | return 0 | YES (ib_device_get_netdev, non‑NULL) | YES (dev_put) | ✅ balanced (refcount) | No double‑put, but if active_dev came from get_hr_netdev with a ref, that ref is leaked. |
| L108 (goto out, ib_device_set_netdev error) | return ret | YES (ib_device_get_netdev, set_netdev failed → ref not released) | YES (dev_put) | ✅ balanced | Same active_dev leak possibility. |
| L116 (fall‑through out, ib_device_set_netdev success) | return 0 | YES (ib_device_get_netdev) but **released by ib_device_set_netdev** per contract | YES (dev_put) → **extra release** | ❌ BUG: double put | `ib_device_set_netdev` already calls `netdev_put(old)`; the later `dev_put(old_dev)` over‑releases the refcount (underflow). |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`ib_device_set_netdev` releases the old net_dev reference on success; the unconditional `dev_put(old_dev)` at `out` then double-puts, causing a refcount underflow.
```
