# REAL BUG: drivers/gpu/drm/rockchip/cdn-dp-reg.c:961 cdn_dp_audio_config()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

rol_assert` at line 939 is **not** a matching put for the subsequent `reset_control_deassert` at line 940 — it is a prior operation that may or may not decrement the counter. The `deassert` unconditionally increments `deassert_count`, requiring a later `assert` which is missing on all error paths.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L945 | goto err_audio_config (CM_LANE_CTRL write failed) | YES (if SPDIF) | NO | ❌ LEAK | `reset_control_deassert` at L940 increments `deassert_count`, but `err_audio_config` does not call `reset_control_assert` |
| L949 | goto err_audio_config (CM_CTRL write failed) | YES (if SPDIF) | NO | ❌ LEAK | Same missing assert on error path |
| L961 | return ret (fallthrough after AUDIO_PACK_CONTROL write; ret may be non-zero) | YES (if SPDIF) | NO | ❌ LEAK | final `cdn_dp_reg_write` failure still returns without assert; success path may intentionally hold the deassert, but error path leaks |
| (non-SPDIF) any | normal return | NO | N/A | ✅ | the `if` block not entered, no deassert |

**Note**: `reset_control_assert` at line 939 is **not** a matching put for the subsequent `reset_control_deassert` at line 940 — it is a prior operation that may or may not decrement the counter. The `deassert` unconditionally increments `deassert_count`, requiring a later `assert` which is missing on all error paths.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_deassert` at L940 unconditionally incref; two error goto paths at L945 and L949, and the fallthrough error from the final register write, all return without calling `reset_control_assert`, leaking the deassert reference.
```
