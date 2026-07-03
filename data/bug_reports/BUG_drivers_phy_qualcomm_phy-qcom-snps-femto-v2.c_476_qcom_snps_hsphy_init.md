# REAL BUG: drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c:476 qcom_snps_hsphy_init()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L425 | return ret; (used by L405/L413/L399) | varies | varies | ❌ on L405/L413 | Error paths that hit L425 from assert/deassert failures are unbalanced |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L394 | error (regulator enable fail) | NO (before deassert) | NO (before assert) | ✅ | No reset calls executed |
| L399 | goto poweroff_phy (clk enable fail) | NO | NO | ✅ | No reset calls executed |
| L405 | goto disable_clks (assert fail) | NO | YES (assert called) | ❌ EXCESS PUT | assert performed, no deassert to balance |
| L413 | goto disable_clks (deassert fail) | **NO (deassert fails)** | YES (assert succeeded) | ❌ EXCESS PUT | assert done, deassert not acquired on failure |
| L418 | success return 0 | YES (deassert success) | YES (assert done) | ✅ | Both calls succeeded, net zero |
| L425 | return ret; (used by L405/L413/L399) | varies | varies | ❌ on L405/L413 | Error paths that hit L425 from assert/deassert failures are unbalanced |

**PRE-VERDICT CHECKLIST:**
1. **“Held for device lifetime”?** – Not applicable; probe lifetime pattern does not cover init error paths.
2. **“Ownership transferred”?** – No transfer; the assert/deassert pair is local to this function.
3. **Unconditional GET?** – `reset_control_deassert` is conditional GET (only increments on success), so error path L413 lacks GET.
4. **goto out between GET and PUT?** – L405 and L413 jump to labels that do not execute any `reset_control_assert` (the only PUT is the earlier L402 call), leaving the assert unbalanced.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`reset_control_assert` at L402 is called unconditionally before any deassert, and two error paths (L405, L413) skip the matching deassert, causing an excess put on `deassert_count`.
```
