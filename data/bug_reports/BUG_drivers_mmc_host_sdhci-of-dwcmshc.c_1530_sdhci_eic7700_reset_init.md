# REAL BUG: drivers/mmc/host/sdhci-of-dwcmshc.c:1530 sdhci_eic7700_reset_init()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

L1527 | error (deassert fails)| NO (deassert failed → no increment) | YES (assert succeeded → decremented) | ❌ EXCESS PUT | PUT happened, GET did not → counter negative |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1515 | error (IS_ERR)       | NO (before any get) | NO (before any put) | ✅ | reset control never acquired |
| L1521 | error (assert fails) | NO (deassert not called) | NO (assert failed → counter unchanged) | ✅ | assert returning error implies no decrement |
| L1527 | error (deassert fails)| NO (deassert failed → no increment) | YES (assert succeeded → decremented) | ❌ EXCESS PUT | PUT happened, GET did not → counter negative |
| L1530 | success (deassert ok) | YES (deassert succeeded) | YES (assert succeeded) | ✅ | balanced assert/deassert sequence |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**
`reset_control_assert()` succeeded at L1518 (PUT), then `reset_control_deassert()` fails at L1524, but the error return at L1527 does not balance the earlier PUT, leaving deassert_count negative (excess put).
```
