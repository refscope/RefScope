# REAL BUG: drivers/hsi/controllers/omap_ssi_core.c:155 ssi_waketest()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L155 (end of else) | function return (void) | NO | YES | ❌ NO | pm_runtime_put called unconditionally when `wktest` is false, regardless of whether a prior get_sync succeeded. If no reference was ever taken (first call with enable=0, or previous get_sync failed), this is an excess put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L151 (end of if) | function return (void) | CONDITIONAL (pm_runtime_get_sync success: YES; failure: NO) | NO | DEPENDS | Return value ignored; if get failed, no ref taken, balanced for that call, but wktest still set to true, leading to future unbalanced put. |
| L155 (end of else) | function return (void) | NO | YES | ❌ NO | pm_runtime_put called unconditionally when `wktest` is false, regardless of whether a prior get_sync succeeded. If no reference was ever taken (first call with enable=0, or previous get_sync failed), this is an excess put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unchecked return value of `pm_runtime_get_sync` at L149 allows `wktest` to be set true without a reference, and subsequent disable (L148 false) always calls `pm_runtime_put` at L155, leading to an excess put on the power.usage_count counter when the prior get failed or never happened.
```
