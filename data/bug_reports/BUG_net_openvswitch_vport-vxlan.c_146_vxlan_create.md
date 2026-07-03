# REAL BUG: net/openvswitch/vport-vxlan.c:146 vxlan_create()

**Confidence**: HIGH | **Counter**: `$->dev->dev_refcnt.refs.counter`

## Reasoning

| L146 | success/error (return ovs_netdev_link) | YES | YES (ovs_netdev_link unconditional PUT) | ✅ | PUT done even if ovs_netdev_link fails. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L144 | error (IS_ERR guard) | YES (vxlan_tnl_create unconditional GET) | NO | ❌ LEAK | Returns ERR_PTR without releasing netdev ref. |
| L146 | success/error (return ovs_netdev_link) | YES | YES (ovs_netdev_link unconditional PUT) | ✅ | PUT done even if ovs_netdev_link fails. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`vxlan_tnl_create()` is an unconditional get (always holds a netdev ref). The error path at line 144 returns without calling the matching `ovs_netdev_link()` put, leaking the refcount.
```
