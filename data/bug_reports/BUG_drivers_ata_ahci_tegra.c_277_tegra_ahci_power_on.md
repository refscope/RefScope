# REAL BUG: drivers/ata/ahci_tegra.c:277 tegra_ahci_power_on()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L266 (success return) | success return | YES (2x deassert at L263‑264) | YES (2x assert at L256‑257) | ✅ | balanced (assert then deassert) |

## Full Response

```
| Line | Return Type | GET Done? (deassert) | PUT Done? (assert) | Balanced? | Notes |
|------|-------------|----------------------|---------------------|-----------|-------|
| L246 | error return (regulator fail) | NO | NO | ✅ | before any reset ops |
| L253 (goto disable_regulators) | error goto → L277 | NO | NO | ✅ | powergate fail, no reset ops yet |
| L261 (goto disable_power) | error goto → L277 | NO | YES (2x assert at L256‑257) | ❌ Excess PUT | asserts done, deasserts skipped → net −2 on deassert_count |
| L266 (success return) | success return | YES (2x deassert at L263‑264) | YES (2x assert at L256‑257) | ✅ | balanced (assert then deassert) |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
On the error path when `ahci_platform_enable_resources()` fails, the two `reset_control_assert()` calls at L256–257 are executed but the matching `reset_control_deassert()` calls are never reached. This leaves the `deassert_count` reference counter with an excess put (net −2), violating the required assert/deassert balance.
```
