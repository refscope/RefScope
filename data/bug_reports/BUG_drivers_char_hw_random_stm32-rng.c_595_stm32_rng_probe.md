# REAL BUG: drivers/char/hw_random/stm32-rng.c:595 stm32_rng_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

priv->rst valid) | NO | ❌ LEAK | registration error exits without asserting |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L541 | error (-ENOMEM) | NO (before any reset_get) | N/A | ✅ | |
| L545 | error (PTR_ERR(priv->base)) | NO (before reset_get) | N/A | ✅ | |
| L560 | error (-ENODEV, priv->data NULL) | YES (if priv->rst valid) | NO | ❌ LEAK | reset deasserted, not asserted on error |
| L569 | error (-EINVAL, nb_clock invalid) | YES (if priv->rst valid) | NO | ❌ LEAK | same |
| L573 | error (dev_err_probe after clk bulk get) | YES (if priv->rst valid) | NO | ❌ LEAK | same |
| L580 | error (dev_err_probe missing clock name) | YES (if priv->rst valid) | NO | ❌ LEAK | same |
| L595 (error) | error (devm_hwrng_register fails) | YES (if priv->rst valid) | NO | ❌ LEAK | registration error exits without asserting |
| L595 (success) | success (devm_hwrng_register succeeds) | YES (if priv->rst valid) | NO (in probe) | ❓ (depends on remove) | remove() may assert, but probe itself never asserts, so from probe's perspective no release |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_deassert()` at L21 is not balanced by `reset_control_assert()` on any error path after L22; all returns after the deassert block (L560, L569, L573, L580, L595) leak the deassert reference when `priv->rst` is valid. The error path of `devm_hwrng_register` at L595 is especially a direct leak even if the success path relies on remove callback.
```
