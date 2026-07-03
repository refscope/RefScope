# REAL BUG: drivers/iio/common/hid-sensors/hid-sensor-trigger.c:173 hid_sensor_power_state()

**Confidence**: HIGH | **Counter**: `st->user_requested_state.counter`

## Reasoning

| Non-CONFIG_PM paths (atomic_set) | – | N/A (atomic_set) | N/A | N/A | no atomic_inc/dec |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L170 (state==true, ret<0) | error | YES (atomic_inc at L162) | NO (no atomic_dec) | ❌ LEAK | refcount incremented but never decremented on pm_runtime_resume_and_get failure |
| L172 (state==true, ret>=0) | success | YES | NO (paired externally) | ✅ | normal lifecycle: counter stays incremented until hid_sensor_power_state(false) |
| L170 (state==false, ret<0) | error | NO | N/A | ✅ | only decremented, no GET |
| L172 (state==false, ret>=0) | success | NO | N/A | ✅ | only decremented |
| Non-CONFIG_PM paths (atomic_set) | – | N/A (atomic_set) | N/A | N/A | no atomic_inc/dec |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When state==true, atomic_inc is unconditional. If pm_runtime_resume_and_get fails (ret<0), the function returns immediately without a matching atomic_dec, permanently corrupting st->user_requested_state.
```
