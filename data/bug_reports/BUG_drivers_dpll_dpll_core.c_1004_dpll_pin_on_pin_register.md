# REAL BUG: drivers/dpll/dpll_core.c:1004 dpll_pin_on_pin_register()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L991 | success     | YES                           | NO (intentionally held for pin lifetime) | ⚠️ (not a leak) | success path retains ref for pin→parent binding; not a bug |

## Full Response

```
| Line | Return Type | GET Done? (dpll_xa_ref_pin_add) | PUT Done? (dpll_xa_ref_pin_del) | Balanced? | Notes |
|------|-------------|--------------------------------|--------------------------------|-----------|-------|
| L970 | early error | NO (before add)                | N/A                            | ✅ | WARN_ON before any get |
| L975 | early error | NO (before add)                | N/A                            | ✅ | WARN_ON before any get |
| L980 | goto unlock | YES (unconditional, called L979) | NO (unlock label only mutex_unlock) | ❌ LEAK | dpll_xa_ref_pin_add failed but ref already inc'd, no corresponding del |
| L987 | goto dpll_unregister (from loop) | YES (still held) | YES (via dpll_xa_ref_pin_del at L1004) | ✅ | error midway through registration, proper cleanup |
| L991 | success     | YES                           | NO (intentionally held for pin lifetime) | ⚠️ (not a leak) | success path retains ref for pin→parent binding; not a bug |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
dpll_xa_ref_pin_add() is an unconditional get (contract), but the early error path `if (ret) goto unlock` returns without calling dpll_xa_ref_pin_del(), leaking the refcount on `$->refcount.refs.counter`.
```
