# REAL BUG: drivers/gpu/drm/msm/disp/mdp5/mdp5_kms.c:569 mdp5_kms_init()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L567 | return 0 (success) | YES | YES | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L508 | return ret (error from mdp5_init) | NO (before get) | N/A | ✅ | |
| L516 | goto fail (error from mdp_kms_init) | NO (before get) | N/A | ✅ | fail does mdp5_kms_destroy, no get held |
| L544 | goto fail (IS_ERR(vm) error) | YES (get at L528) | NO | ❌ LEAK | fail label lacks pm_runtime_put_sync |
| L552 | goto fail (modeset_init error) | YES (get at L528) | YES (put at L548) | ✅ | put already called before modeset_init |
| L567 | return 0 (success) | YES | YES | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` at L528 assumes success (return not checked), but the IS_ERR(vm) error path (L544 `goto fail`) skips `pm_runtime_put_sync` at L548, leaking a reference.
```
