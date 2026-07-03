# REAL BUG: drivers/net/ethernet/freescale/fman/fman.c:2823 read_dts_node()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| return fman at ~2811 (success) | success | YES | NO | ❌ LEAK | fm_node never put, no ownership transfer |

## Full Response

```
| Line | Return Type | GET Done? (fm_node) | PUT Done? (fm_node) | Balanced? | Notes |
|------|-------------|---------------------|----------------------|-----------|-------|
| ~2693 (kzalloc fail) | error, ERR_PTR(-ENOMEM) | NO (before get) | N/A | ✅ | before of_node_get |
| goto fman_node_put at ~2716 (of_property_read_u32 fail) | error | YES | YES (of_node_put at fman_node_put label) | ✅ | |
| goto fman_node_put at ~2721 (platform_get_irq 0 fail) | error | YES | YES | ✅ | |
| goto fman_node_put at ~2726 (platform_get_irq 1 fail) | error | YES | YES | ✅ | |
| goto fman_node_put at ~2734 (IS_ERR(clk)) | error | YES | YES | ✅ | |
| goto fman_node_put at ~2742 (clk_rate == 0) | error | YES | YES | ✅ | |
| goto fman_node_put at ~2750 (of_property_read_u32_array fail) | error | YES | YES | ✅ | |
| goto fman_free at ~2764 (muram_node NULL) | error | YES | NO | ❌ LEAK | fman_free label does not put fm_node |
| goto fman_free at ~2772 (of_address_to_resource fail) | error | YES | NO | ❌ LEAK | muram_node put, but fm_node not put |
| goto fman_free at ~2780 (devm_request_irq fail) | error | YES | NO | ❌ LEAK | |
| goto fman_free at ~2790 (devm_request_irq err_irq fail) | error | YES | NO | ❌ LEAK | |
| goto fman_free at ~2797 (base_addr IS_ERR) | error | YES | NO | ❌ LEAK | |
| goto fman_free at ~2805 (of_platform_populate fail) | error | YES | NO | ❌ LEAK | |
| return fman at ~2811 (success) | success | YES | NO | ❌ LEAK | fm_node never put, no ownership transfer |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unconditional of_node_get(fm_node) at L2697 leaks on all goto fman_free error paths and the success return; fman_free label lacks of_node_put(fm_node), and fman does not store the node for later release.
```
