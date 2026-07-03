# REAL BUG: net/openvswitch/vport-netdev.c:160 netdev_create()

**Confidence**: LOW | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

| L156 (return ovs_netdev_link(...)) | success/error | YES | NO (not in this func) | ❓ LEAK? | ref held from dev_get_by_name; not released in this path; whether ovs_netdev_link transfers ownership and handles the ref is unknown → [NEED_SOURCE] ovs_netdev_link |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L130 (return IS_ERR(vport)) | error | NO (before get) | N/A | ✅ | get hasn't happened |
| L138 (goto error_free_vport after NULL dev) | error | NO (get failed, NULL) | N/A | ✅ | dev_get_by_name returned NULL, no ref held |
| L145 (goto error_put after strcmp fail) | error | YES | YES (netdev_put in error_put) | ✅ | explicit release before free |
| L153 (goto error_put after flags/type fail) | error | YES | YES (netdev_put) | ✅ | same |
| L156 (return ovs_netdev_link(...)) | success/error | YES | NO (not in this func) | ❓ LEAK? | ref held from dev_get_by_name; not released in this path; whether ovs_netdev_link transfers ownership and handles the ref is unknown → [NEED_SOURCE] ovs_netdev_link |

VERDICT: REAL_BUG
CONFIDENCE: LOW
Success path exits without netdev_put; unless ovs_netdev_link takes ownership and arranges an eventual put (e.g., on vport destruction), the dev reference acquired by dev_get_by_name is leaked.
```
