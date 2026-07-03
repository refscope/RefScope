# REAL BUG: drivers/infiniband/hw/mana/device.c:236 mana_ib_probe()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

| L214 | return 0 (success) | YES | YES (normal removal path releases) | ✅ | device registered, cleanup later |

## Full Response

```
| Line | Return Type | GET Done? (ib_device_set_netdev) | PUT Done? (unset netdev) | Balanced? | Notes |
|------|-------------|----------------------------------|--------------------------|-----------|-------|
| L128 | return -ENOMEM | NO (before any netdev) | N/A | ✅ | |
| L143 | goto free_ib_device | NO (before netdev) | N/A | ✅ | |
| L154 | goto free_ib_device | NO (before netdev) | N/A | ✅ | |
| L159 | goto destroy_eqs | NO (before netdev) | N/A | ✅ | |
| L169 | goto destroy_rnic (ndev NULL) | NO | N/A | ✅ | |
| L177 | goto destroy_rnic (ib_device_set_netdev error) | NO (set failed, no ref held) | N/A | ✅ | netdev_put already called on ndev from mana_get; set didn't take ref |
| L182 | goto destroy_rnic (config_mac error) | YES (ib_device_set_netdev succeeded for this port) | NO | ❌ LEAK | ib device holds ref; also previous ports if loop >0 |
| L189 | goto destroy_rnic (register notifier fail) | YES (all ports set) | NO | ❌ LEAK | all ib_device_set_netdev refs held |
| L196 | goto free_ib_device (ETH else) | NO (no netdev) | N/A | ✅ | |
| L203 | goto deregister_net_notifier (dma_pool_create fail) | YES (all ports set) | NO | ❌ LEAK | |
| L210 | goto deallocate_pool (ib_register_device fail) | YES (all ports set) | NO | ❌ LEAK | |
| L214 | return 0 (success) | YES | YES (normal removal path releases) | ✅ | device registered, cleanup later |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ib_device_set_netdev()` holds a netdev reference on success; on probe error paths (L182, L189, L203, L210) the function jumps to cleanup labels that never release these references (no `ib_device_set_netdev(..., NULL)`), leaking the netdev refcount.
```
