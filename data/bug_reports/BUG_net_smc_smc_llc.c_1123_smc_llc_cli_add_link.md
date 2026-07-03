# REAL BUG: net/smc/smc_llc.c:1123 smc_llc_cli_add_link()

**Confidence**: HIGH | **Counter**: `$->smcibdev->lnk_cnt.counter`

## Reasoning

| L1132  | out_clear_lnk (error) | YES | YES | ✅ | conf_link fail clears |

## Full Response

```
| Line   | Return Type          | GET Done? | PUT Done? | Balanced? | Notes |
|--------|----------------------|-----------|-----------|-----------|-------|
| L1038  | goto out_reject      | NO (before alloc) | N/A | ✅ | qp_mtu check |
| L1043  | goto out_reject      | NO (before alloc) | N/A | ✅ | ini alloc failed |
| L1048  | goto out_reject      | NO (before alloc) | N/A | ✅ | single link group check |
| L1079  | goto out_reject      | NO (before alloc) | N/A | ✅ | no ib_dev |
| L1092  | goto out_reject      | NO (alloc_alt_link failed) | N/A | ✅ | allocation failed |
| L1100  | goto out_reject      | YES | NO | ❌ **LEAK** | smcr_link_init failed, link not cleared |
| L1109  | goto out_clear_lnk   | YES | YES (smcr_link_clear) | ✅ | smc_ib_ready_link fail |
| L1113  | goto out_clear_lnk   | YES | YES | ✅ | smcr_buf_map_lgr fail |
| L1118  | goto out_clear_lnk   | YES | YES | ✅ | send_add_link fail |
| L1123  | goto out_clear_lnk   | YES | YES | ✅ | cli_rkey_exchange fail, rc=0 |
| L1131  | goto out (success)   | YES | NO (intentional) | ✅ | conf_link success, link stays |
| L1132  | out_clear_lnk (error) | YES | YES | ✅ | conf_link fail clears |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After `smc_llc_alloc_alt_link` succeeds and `smcr_link_init` fails, the code jumps to `out_reject` without calling `smcr_link_clear`, leaking the reference taken for the new link (and leaving the link uninitialised but not cleaned up).
```
