# REAL BUG: drivers/counter/ti-eqep.c:561 ti_eqep_probe()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L560 | success (0) | YES | NO (held for device lifetime) | ✅ (if remove releases) | held for device lifetime, not a leak in probe |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L505 | error (-ENOMEM) | NO (before get) | N/A | ✅ | |
| L510 | error (PTR_ERR) | NO | N/A | ✅ | |
| L515 | error (PTR_ERR) | NO | N/A | ✅ | |
| L520 | error (PTR_ERR) | NO | N/A | ✅ | |
| L524 | error (irq <0) | NO | N/A | ✅ | |
| L529 | error (dev_err_probe) | NO | N/A | ✅ | |
| L551 | error (dev_err_probe, clock fail) | YES (pm_runtime_get_sync succeeded) | NO | ❌ LEAK | clk error path leaks runtime PM ref |
| L557 | error (return err after counter_add failure) | YES | YES (pm_runtime_put_sync) | ✅ | put then disable |
| L560 | success (0) | YES | NO (held for device lifetime) | ✅ (if remove releases) | held for device lifetime, not a leak in probe |
```

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**

The error path for `devm_clk_get_enabled` failure (L551) returns without releasing the runtime PM reference acquired by `pm_runtime_get_sync` at L547. The success path correctly holds the reference for device lifetime (to be released in remove), but error paths before a successful probe must explicitly put. The `counter_add` error path does put, but the clock error path does not.
```
