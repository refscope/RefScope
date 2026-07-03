# REAL BUG: drivers/hwmon/npcm750-pwm-fan.c:1029 npcm7xx_pwm_fan_probe()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

Given the pattern (scoped auto‑put on nodes that are passed to a “_en_” function and likely retained), the missing `of_node_get` in the probe is the root cause of the eventual refcount underflow.

## Full Response

```
| Line | Return Type | GET Done? (child) | PUT Done? (child) | Balanced? | Notes |
|------|-------------|-------------------|-------------------|-----------|-------|
| L937 | error       | NO (before child loop) | N/A  | ✅ | no child node involved |
| L941 | error       | NO (before child loop) | N/A  | ✅ | |
| L948 | error       | NO (before child loop) | N/A  | ✅ | |
| L954 | error       | NO (before child loop) | N/A  | ✅ | |
| L959 | error       | NO (before child loop) | N/A  | ✅ | |
| L965 | error       | NO (before child loop) | N/A  | ✅ | |
| L971 | error       | NO (before child loop) | N/A  | ✅ | |
| L976 | error       | NO (before child loop) | N/A  | ✅ | |
| L987 | error       | NO (before child loop) | N/A  | ✅ | |
| L994 | error       | NO (before child loop) | N/A  | ✅ | |
| L1002| error       | YES (scoped macro) | YES (scoped macro cleanup before return) | ✅ | macro puts child; error branch still runs cleanup |
| L1011| error       | YES (loop exited) | YES (per‑iteration scoped puts) | ✅ | all children put |
| L1029| success     | YES (loop exited) | YES (per‑iteration scoped puts) | ✅ | all children put |

`for_each_child_of_node_scoped` internally calls `of_get_next_child` (GET) and automatically calls `of_node_put` (PUT) at the end of each iteration’s scope. All return paths that encounter the loop either pass through the automatic cleanup or exit the function while still inside the loop body, where the scoped cleanup is guaranteed to run. From the probe function’s perspective, every child reference acquired is released, so the function itself does not directly leak or cause an excess put.

However, the warning is “refcount excess put on $->kobj.kref.refcount.counter” at line 1029, which is the probe’s `return 0`. This suggests that a later `of_node_put` on a child node underflows the refcount. That will happen if the driver (likely in its remove path, or in `npcm7xx_en_pwm_fan`) expects the child node to remain referenced after the probe returns, but the probe’s scoped loop already dropped the reference. The probe therefore **fails to acquire a long-term reference** to the child node, making the eventual put an excess one.

The function `npcm7xx_en_pwm_fan` is the likely place where the child node pointer may be stored for later cleanup. To confirm this, the source of `npcm7xx_en_pwm_fan` is needed.

[NEED_SOURCE] npcm7xx_en_pwm_fan

Given the pattern (scoped auto‑put on nodes that are passed to a “_en_” function and likely retained), the missing `of_node_get` in the probe is the root cause of the eventual refcount underflow.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
```
