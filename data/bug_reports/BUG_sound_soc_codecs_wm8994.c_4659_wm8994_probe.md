# REAL BUG: sound/soc/codecs/wm8994.c:4659 wm8994_probe()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

ore error) | **YES** (pm_runtime_disable does a put_noidle, leading to underflow) | ❌ EXCESS PUT | usage_count was 0; pm_runtime_disable causes atomic decrement below zero |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (pm_runtime_get) | PUT Done? (pm_runtime_put-like) | Balanced? | Notes |
|------|-------------|----------------------------|----------------------------------|-----------|-------|
| L4634 | error (ENOMEM) | NO (before pm_runtime_enable) | NO | ✅ | early exit, no PM operations |
| L4647 | error (clk fail) | NO (before pm_runtime_enable) | NO | ✅ | early exit, no PM operations |
| L4661 (via L4655 ret<0) | error (register fail) | **NO** (no usage_count increment before error) | **YES** (pm_runtime_disable does a put_noidle, leading to underflow) | ❌ EXCESS PUT | usage_count was 0; pm_runtime_disable causes atomic decrement below zero |
| L4661 (success ret≥0) | success | **NO** | **NO** | ✅ | normal probe success; runtime PM remains enabled with count 0 |

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  

`pm_runtime_enable` initializes runtime power management but does **not** increment `power.usage_count` (starts at 0). `pm_runtime_idle` also leaves the count unchanged (net zero). If `devm_snd_soc_register_component` fails, the error path calls `pm_runtime_disable()`, which internally performs a `pm_runtime_put_noidle()` — immediately underflowing the zero-initialised counter. This is a classic **unmatched `pm_runtime_disable` without a prior `pm_runtime_get`**, generating the `refcount excess put` warning. The fix is to remove the erroneous `pm_runtime_disable` on that error path.
```
