# REAL BUG: drivers/mmc/core/pwrseq_simple.c:76 mmc_pwrseq_simple_pre_power_on()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L77 (implicit return) | void | Conditional: YES only if reset_control_deassert() succeeds, NO on error | YES (unconditional reset_control_assert() always reached) | NO if deassert fails | Ignored return value of deassert; on failure, assert is still called → underflow of deassert_count |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L77 (implicit return) | void | Conditional: YES only if reset_control_deassert() succeeds, NO on error | YES (unconditional reset_control_assert() always reached) | NO if deassert fails | Ignored return value of deassert; on failure, assert is still called → underflow of deassert_count |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
reset_control_deassert() return value is ignored – if it fails (does not increment deassert_count), the subsequent reset_control_assert() will decrement an already-zero counter, causing refcount excess put.
```
