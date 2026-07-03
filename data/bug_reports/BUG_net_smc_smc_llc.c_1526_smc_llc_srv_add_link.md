# REAL BUG: net/smc/smc_llc.c:1526 smc_llc_srv_add_link()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L1504 | return 0 (success) | YES | NO (not needed) | ✅ | Link now active, ref held for lifetime |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1417 | goto out (ini alloc fail) | NO | N/A | ✅ | Before smcr_link_init |
| L1424 | goto out (SINGLE max_links≤1) | NO | N/A | ✅ | Before smcr_link_init |
| L1452 | goto out (alloc_alt_link fail) | NO | N/A | ✅ | Before smcr_link_init |
| L1458 | goto out (smcr_link_init fail) | **YES** (unconditional get) | **NO** | ❌ LEAK | out label skips smcr_link_clear; link_new is NULL so out_err would not clear either, but clear needed to release ref acquired by smcr_link_init |
| L1462 | goto out_err (smcr_buf_map_lgr fail) | YES | YES (out_err → smcr_link_clear) | ✅ | |
| L1466 | goto out_err (send_add_link fail) | YES | YES | ✅ | |
| L1471 | goto out_err (wait timeout) | YES | YES | ✅ | |
| L1477 | goto out_err (ADD_LNK_REJ) | YES | YES | ✅ | |
| L1488 | goto out_err (smc_ib_ready_link fail) | YES | YES | ✅ | |
| L1490 | goto out_err (smcr_buf_reg_lgr fail) | YES | YES | ✅ | |
| L1499 | goto out_err (rkey exchange fail) | YES | YES | ✅ | |
| L1502 | goto out_err (smc_llc_srv_conf_link fail) | YES | YES | ✅ | |
| L1504 | return 0 (success) | YES | NO (not needed) | ✅ | Link now active, ref held for lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`smcr_link_init` is an unconditional GET; its only error path (goto out at L1458) never calls `smcr_link_clear`, leaking the reference it acquired.
```
