# REAL BUG: drivers/gpu/drm/msm/disp/mdp5/mdp5_crtc.c:1077 mdp5_crtc_cursor_move()

**Confidence**: HIGH | **Counter**: `mdp5_kms->pdev->dev.power.usage_count.counter`

## Reasoning

t checking its return value. The contract states that if the return is `<0`, no refcount increment occurs. The code proceeds unconditionally to the `pm_runtime_put_sync()` at L1072, which will trigger an underflow when the prior get failed. The warning (“refcount excess put”) is therefore genuine.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1050 | error return | NO (before get) | N/A | ✅ | early return: lm_cursor not enabled |
| L1054 | error return | NO (before get) | N/A | ✅ | early return: source split enabled |
| L1057 | return 0      | NO (before get) | N/A | ✅ | early return: CRTC disabled |
| L1074 (end) | return 0 | YES (pm_runtime_get_sync called) | YES (pm_runtime_put_sync called) | ⚠️ GET may not have incremented if return < 0 → PUT becomes an excess put (underflow) | Return value of `pm_runtime_get_sync` not checked; on failure it does **not** increment the usage counter, but a `pm_runtime_put_sync` is still executed → counter underflow → excess put warning |

**Analysis**:  
`pm_runtime_get_sync()` is called at L1064 without checking its return value. The contract states that if the return is `<0`, no refcount increment occurs. The code proceeds unconditionally to the `pm_runtime_put_sync()` at L1072, which will trigger an underflow when the prior get failed. The warning (“refcount excess put”) is therefore genuine.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Missing `pm_runtime_get_sync` return‑value check can cause an excess put when the get fails.
```
