# REAL BUG: drivers/gpu/drm/bridge/adv7511/adv7511_drv.c:1420 adv7511_probe()

**Confidence**: HIGH | **Counter**: `adv7511->host_node->kobj.kref.refcount.refs.counter`

## Reasoning

| L? (success return 0) | success | YES | NO (retained for device lifetime) | N/A (intentional) | ✅ |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L? (early: !of_node) | error | NO (before get) | N/A | ✅ | |
| L? (IS_ERR(adv7511)) | error | NO | N/A | ✅ | |
| L? (drm_of_find… ret) | error | NO | N/A | ✅ | |
| L? (parse_dt ret error) | error | YES (host_node set) | NO | ❌ LEAK | returns ret directly without of_node_put |
| L? (goto err_of_node_put) | error | YES | YES (via err_of_node_put) | ✅ | |
| L? (goto uninit_regulators) | error | YES | YES (fallthrough to err_of_node_put) | ✅ | |
| L? (goto err_i2c_unregister_edid) | error | YES | YES (fallthrough) | ✅ | |
| L? (goto err_i2c_unregister_packet) | error | YES | YES (fallthrough) | ✅ | |
| L? (goto err_unregister_audio) | error | YES | YES (fallthrough) | ✅ | |
| L? (success return 0) | success | YES | NO (retained for device lifetime) | N/A (intentional) | ✅ |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`adv7533_parse_dt` unconditionally obtains a reference to `adv7511->host_node`, but if it returns an error, the probe function returns immediately without calling `of_node_put(adv7511->host_node)`, leaking the node.
```
