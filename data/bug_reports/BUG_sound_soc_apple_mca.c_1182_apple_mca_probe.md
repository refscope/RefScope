# REAL BUG: sound/soc/apple/mca.c:1182 apple_mca_probe()

**Confidence**: HIGH | **Counter**: `mca->rstc->triggered_count.counter`

## Reasoning

| ~1180 | return 0 (success) | YES | N/A (deferred to remove) | ✅ | probe success, lifetime managed |

## Full Response

```
| Line | Return Type | GET Done? (trigger count inc) | PUT Done? (rearm) | Balanced? | Notes |
|------|-------------|-------------------------------|-------------------|-----------|-------|
| ~1039 | error (IS_ERR) | NO (before reset) | N/A | ✅ | early return |
| ~1043 | error (-EINVAL) | NO (before reset) | N/A | ✅ | before reset control |
| ~1050 | error (-ENOMEM) | NO (before reset) | N/A | ✅ | |
| ~1059 | error (PTR_ERR) | NO (before reset) | N/A | ✅ | |
| ~1063 | error (PTR_ERR) | NO (rstc get failed) | N/A | ✅ | conditioned on IS_ERR |
| ~1068 | error (-ENOMEM) | NO (before reset) | N/A | ✅ | |
| ~1072 | error (-EINVAL) | NO (before reset) | N/A | ✅ | |
| ~1086 | goto err_release (rstc=NULL) | NO (rstc=NULL, reset not called) | N/A | ✅ | pd_link failure safely clears rstc |
| ~1105 | goto err_release (of_clk_get fail) | YES (reset called) | NO | ❌ LEAK | triggered_count incremented, no rearm |
| ~1113 | goto err_release (pd_dev attach fail) | YES | NO | ❌ LEAK | same |
| ~1130 | goto err_release (fe->name fail) | YES | NO | ❌ LEAK | |
| ~1145 | goto err_release (fe stream_name fail) | YES | NO | ❌ LEAK | |
| ~1160 | goto err_release (be->name fail) | YES | NO | ❌ LEAK | |
| ~1170 | goto err_release (be stream_name fail) | YES | NO | ❌ LEAK | |
| ~1178 | goto err_release (register component fail) | YES | NO | ❌ LEAK | |
| ~1180 | return 0 (success) | YES | N/A (deferred to remove) | ✅ | probe success, lifetime managed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_reset` increments `triggered_count`; all error paths after that call (`goto err_release`) miss the required `reset_control_rearm`/rebalance, and `apple_mca_release` only tears down `device_link`, not the reset reference.
```
