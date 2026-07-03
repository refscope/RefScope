# REAL BUG: drivers/net/dsa/lantiq/lantiq_gswip.c:168 gswip_gphy_fw_load()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L162 | success             | YES (deassert at L161)| YES (assert at L129)| ✅         | Normal path: assert → deassert, balanced. |

## Full Response

```
| Line | Return Type        | GET (deassert) Done? | PUT (assert) Done? | Balanced? | Notes |
|------|---------------------|-----------------------|--------------------|-----------|-------|
| L126 | error               | NO (before assert)    | NO                 | ✅         | clk_prepare_enable fails; no reset ops yet. |
| L139 | error               | NO                    | YES (assert at L129)| ❌ LEAK    | request_firmware fails; assert done but deassert skipped. |
| L153 | error               | NO                    | YES (assert at L129)| ❌ LEAK    | dmam_alloc_coherent fails; assert done, no deassert. |
| L159 | error               | NO                    | YES (assert at L129)| ❌ LEAK    | regmap_write fails; assert done, no deassert. |
| L162 | success             | YES (deassert at L161)| YES (assert at L129)| ✅         | Normal path: assert → deassert, balanced. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_assert()` (PUT) is executed early (L129). Three error returns (L139 request_firmware, L153 dmam_alloc_coherent, L159 regmap_write) skip `reset_control_deassert()` (GET), leaving deassert_count one less than intended and causing a net imbalance.
```
