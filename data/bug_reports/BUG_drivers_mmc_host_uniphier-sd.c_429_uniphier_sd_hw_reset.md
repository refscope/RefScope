# REAL BUG: drivers/mmc/host/uniphier-sd.c:429 uniphier_sd_hw_reset()

**Confidence**: MEDIUM | **Counter**: `$->deassert_count.counter`

## Reasoning

| The function calls `reset_control_assert` (PUT) before `reset_control_deassert` (GET). This is only safe if the reset line was previously deasserted (counter ≥ 1). No check or preceding deassert exists. If `deassert_count` was 0, the assert causes an **excess put**, which matches the warning. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| End (after L430) | void return | YES (deassert at L429) | YES (assert at L425) | ⚠️ Potentially not, if initial deassert_count was 0 | The function calls `reset_control_assert` (PUT) before `reset_control_deassert` (GET). This is only safe if the reset line was previously deasserted (counter ≥ 1). No check or preceding deassert exists. If `deassert_count` was 0, the assert causes an **excess put**, which matches the warning. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`uniphier_sd_hw_reset()` unconditionally calls `reset_control_assert()` (a PUT that decrements deassert_count), then later `reset_control_deassert()` (a GET). If the reset line is already asserted (deassert_count=0) when this function is entered, the assert will underflow the counter, triggering an actual "refcount excess put" at runtime. The function lacks a guard or a prior deassert to guarantee a safe state. Despite being locally balanced in terms of call pairing, it does not defend against the unsafe entry condition and therefore represents a real bug.
```
