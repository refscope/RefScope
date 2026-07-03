# REAL BUG: drivers/memory/stm32_omm.c:282 stm32_omm_configure()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L267 (stm32_omm_set_amcr success, ret == 0, falls to error) | success | YES | NO (intentional) | ✅ | Reset stays deasserted for operation |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L198 (devm_clk_bulk_get error) | error | NO (before deassert) | N/A | ✅ | No reset get/deassert yet |
| L202 (stm32_omm_disable_child error) | error | NO | N/A | ✅ | Before reset deassert |
| L205 (pm_runtime_resume_and_get error) | error | NO | N/A | ✅ | Before reset deassert |
| L215 (goto error: invalid clock rate) | error | NO | N/A | ✅ | Before reset deassert |
| L225 (goto error: IS_ERR(rstc)) | error | NO | N/A | ✅ | Before reset deassert |
| **After reset_control_deassert at L235** | | | | | |
| L256 (goto error: stm32_omm_toggle_child_clock fails) | error (ret != 0) | YES | NO | ❌ LEAK | Forgot reset_control_assert |
| L267 (stm32_omm_set_amcr fails, ret != 0, falls to error) | error (ret != 0) | YES | NO | ❌ LEAK | No assert before return |
| L267 (stm32_omm_set_amcr success, ret == 0, falls to error) | success | YES | NO (intentional) | ✅ | Reset stays deasserted for operation |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After reset_control_deassert at line 235, two error paths (goto error at L256 and fall-through with non-zero ret after stm32_omm_set_amcr) return without calling reset_control_assert, leaking the deassert_count refcount.
```
