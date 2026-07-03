# REAL BUG: drivers/mailbox/imx-mailbox.c:960 imx_mu_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L960 | (fallthrough) | depends on path; for L946/L950 leads to unbalanced return | – | ⚠️ | return of error code, leak persists on those error paths |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L866 | error       | NO (before populate) | N/A | ✅ | |
| L872 | error       | NO | N/A | ✅ | |
| L876 | error       | NO | N/A | ✅ | |
| L881 | error       | NO | N/A | ✅ | |
| L884 | error       | NO | N/A | ✅ | |
| L888 | error       | NO | N/A | ✅ | |
| L901 | error       | NO | N/A | ✅ | |
| L906 | error       | NO | N/A | ✅ | |
| L914 | error       | NO | N/A | ✅ | |
| L924 | goto disable_clk | NO (populate not yet called) | N/A | ✅ | |
| L938 | goto disable_clk | NO (populate not yet called) | N/A | ✅ | |
| L946 | goto disable_runtime_pm | YES (populate called at L940) | NO (no of_platform_depopulate) | ❌ LEAK | |
| L950 | goto disable_runtime_pm | YES | NO | ❌ LEAK | |
| L954 | success     | YES | NO | ✅ | children are kept for device lifetime |
| L960 | (fallthrough) | depends on path; for L946/L950 leads to unbalanced return | – | ⚠️ | return of error code, leak persists on those error paths |
```

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**

Missing `of_platform_depopulate(dev)` on error paths after `of_platform_populate()` (L940) leaks child device references to the parent device's kref, causing the inconsistent refcounting warning at L960.
```
