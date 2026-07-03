# REAL BUG: net/smc/smc_llc.c:1737 smc_llc_process_srv_delete_link()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| E | ~1712 | fall-through (smc_link_downing=true, smc_switch_conns returns true) | YES (via smc_switch_conns → smc_switch_link_and_count(put)) | YES (smcr_link_clear) | ❌ EXCESS PUT | smc_switch_conns already dropped lnk_del’s ref; smcr_link_clear does second put → underflow |

## Full Response

```
| Path | Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|------|-------------|-----------|-----------|-----------|-------|
| A | ~1685 | goto out (delete entire lgr) | NO | NO | ✅ | smcr_link_clear skipped |
| B | ~1696 | goto out (lnk_del not found) | NO | NO | ✅ | smcr_link_clear skipped |
| C | ~1712 | fall-through (smc_link_downing=false) | NO | YES | ✅ | smcr_link_clear called; normal if link has initial ref |
| D | ~1712 | fall-through (smc_link_downing=true, smc_switch_conns returns false) | NO | YES | ✅ | no extra put from smc_switch_conns |
| E | ~1712 | fall-through (smc_link_downing=true, smc_switch_conns returns true) | YES (via smc_switch_conns → smc_switch_link_and_count(put)) | YES (smcr_link_clear) | ❌ EXCESS PUT | smc_switch_conns already dropped lnk_del’s ref; smcr_link_clear does second put → underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`smc_switch_conns` contract shows it does `smc_switch_link_and_count(put)` on the old link, so when it returns true, `lnk_del`’s ref is already dropped; the unconditional `smcr_link_clear` on line 1737 then performs an excess put, causing a refcount underflow.
```
