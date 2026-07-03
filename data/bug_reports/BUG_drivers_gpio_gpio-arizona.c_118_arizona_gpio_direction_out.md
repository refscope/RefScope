# REAL BUG: drivers/gpio/gpio-arizona.c:118 arizona_gpio_direction_out()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L116 (return regmap_update_bits result) | success/error (call returns) | YES (if condition at L104 was true and get succeeded) | NO | ❌ LEAK | on success path, pm_runtime_get_sync incremented usage_count, but no pm_runtime_put before return |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L101–102 (return ret after regmap_read) | error (regmap_read failed) | NO (before any get) | N/A | ✅ | |
| L110 (return ret after pm_runtime_get_sync error) | error (get failed) | NO (ret < 0 → increment not done) | YES (pm_runtime_put at L109) | ✅ | explicit put on error path |
| L116 (return regmap_update_bits result) | success/error (call returns) | YES (if condition at L104 was true and get succeeded) | NO | ❌ LEAK | on success path, pm_runtime_get_sync incremented usage_count, but no pm_runtime_put before return |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync() increments the usage counter when successful (ret ≥ 0), but the function lacks a matching pm_runtime_put() on that success path; the reference is leaked every time a persistent output direction is changed.
```
