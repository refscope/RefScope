# REAL BUG: drivers/gpu/drm/tegra/rgb.c:281 tegra_dc_rgb_probe()

**Confidence**: MEDIUM | **Counter**: `$->ddc->dev.kobj.kref.refcount.refs.counter`

## Reasoning

[NEED_SOURCE] tegra_output_remove

## Full Response

```
| Line | Return Type | GET Done? (ddc ref) | PUT Done? | Balanced? | Notes |
|------|-------------|----------------------|-----------|-----------|-------|
| L215 | error (-ENODEV) | NO (before probe) | N/A | ✅ | `of_get_child_by_name` failed, no ref |
| L220 | error (err) | NO | N/A | ✅ | `devm_add_action_or_reset` failed, no probe yet |
| L222 | error (-ENODEV) | NO | N/A | ✅ | device unavailable, before probe |
| L227 | error (-ENOMEM) | NO | N/A | ✅ | alloc fail, no probe |
| L235 | error (tegra_output_probe failed) | **UNCERTAIN** – depends on whether `tegra_output_probe` holds ddc ref on failure | NO (`tegra_output_remove` not called) | ❓ POSSIBLE LEAK | If probe acquired ddc kref and didn’t release on error, this path leaks |
| L241 | error (goto remove) | YES | YES (`tegra_output_remove` at L280) | ✅ | IS_ERR guard, goto cleanup |
| L248 | error (goto remove) | YES | YES | ✅ | same |
| L254 | error (goto remove) | YES | YES | ✅ | same |
| L261 | error (goto remove) | YES | YES | ✅ | same |
| L269 | error (goto put_pll) | YES | YES (`clk_put` + fallthrough to `remove`) | ✅ | cleans up pll_d_out0 then output |
| L275 | success (return 0) | YES | NO (deferred to `tegra_output_remove` in device teardown) | ✅ | ownership transferred; remove path handles put |

[NEED_SOURCE] tegra_output_probe
[NEED_SOURCE] tegra_output_remove

**VERDICT: REAL_BUG**  
**CONFIDENCE: MEDIUM**  
`tegra_output_probe` appears to acquire a ddc kref (adapter) that is not released on its error path; the caller at L235 neglects `tegra_output_remove`, causing a leak relative to the balanced remove path at L281.
```
