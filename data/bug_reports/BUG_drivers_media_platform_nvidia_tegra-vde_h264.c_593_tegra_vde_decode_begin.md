# REAL BUG: drivers/media/platform/nvidia/tegra-vde/h264.c:593 tegra_vde_decode_begin()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L579 | return 0 (success) | YES | NO | ⚠️ intentional hold | deassert held for hardware operation, balanced later by decode_end |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L543 | early error (lock fail) | NO (before deassert) | N/A | ✅ | lock interruptible fail |
| L546 | goto unlock (rpm fail) | NO | N/A | ✅ | pm_runtime_resume_and_get failed, no deassert |
| L553 | goto put_runtime_pm (assert fail) | NO | N/A | ✅ | reset_control_assert failed before deassert |
| L559 | goto put_runtime_pm (reset fail) | NO | N/A | ✅ | reset_control_reset failed before deassert |
| L565 | goto put_runtime_pm (deassert fail) | NO (deassert failed) | N/A | ✅ | deassert failed, no ref held |
| L575 | goto put_runtime_pm (setup hw fail) | YES | NO | ❌ LEAK | deassert succeeded, but runtime pm put only, no reset_control_assert |
| L579 | return 0 (success) | YES | NO | ⚠️ intentional hold | deassert held for hardware operation, balanced later by decode_end |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_deassert` succeeds at L562, then `tegra_vde_setup_hw_context` failure (L573) jumps to `put_runtime_pm` without calling `reset_control_assert`, leaking the deassert reference.
```
