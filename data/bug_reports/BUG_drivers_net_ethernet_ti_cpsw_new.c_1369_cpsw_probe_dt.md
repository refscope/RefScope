# REAL BUG: drivers/net/ethernet/ti/cpsw_new.c:1369 cpsw_probe_dt()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1391 | normal loop end, return 0 | YES (last loop ref released by macro) + possible phy_node refs | loop auto‑release; no explicit call | ✅ (success) | success path, phy_node references kept |

## Full Response

```
| Line | Return Type | GET Done? (ref held) | PUT Done? | Balanced? | Notes |
|------|-------------|----------------------|-----------|-----------|-------|
| L1289 | early return | NO | N/A | ✅ | before any get |
| L1294 | early return | NO | N/A | ✅ | |
| L1299 | early return | NO | N/A | ✅ | |
| L1305 | early return | NO | N/A | ✅ | |
| L1310 | early return | NO | N/A | ✅ | |
| L1315 | early return | NO | N/A | ✅ | |
| L1320 | early return | NO | N/A | ✅ | |
| L1345 | goto err_node_put (ifphy error) | YES (loop ref only) | YES (of_node_put(slave_node)) | ✅ | no phy_node yet |
| L1360 | goto err_node_put (fixed‑link reg fail) | YES (loop ref only) | YES (of_node_put(slave_node)) | ✅ | phy_node get not yet done |
| L1369 | goto err_node_put (of_get_phy_mode fail) | YES (loop ref + possible phy_node ref) | YES (loop ref) only, **missing phy_node put** | ❌ LEAK | phy_node may be set via of_parse_phandle or of_node_get(slave_node); error path only releases loop ref |
| L1379 | goto err_node_put (ti_cm_get_macid fail) | YES (loop ref + possible phy_node ref) | YES (loop ref) only, **missing phy_node put** | ❌ LEAK | same as above |
| L1387 | goto err_node_put (i==slaves, ret=0)  | YES (loop ref + possible phy_node ref) | YES (loop ref) only (phy_node held for driver) | ✅ (success) | success exit – phy_node reference is kept for use by the driver |
| L1391 | normal loop end, return 0 | YES (last loop ref released by macro) + possible phy_node refs | loop auto‑release; no explicit call | ✅ (success) | success path, phy_node references kept |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Error paths after `phy_node` is set (via `of_parse_phandle` or `of_node_get` inside the fixed‑link branch) jump to `err_node_put` which only calls `of_node_put(slave_node)`, leaking the extra reference acquired for `phy_node`.
```
