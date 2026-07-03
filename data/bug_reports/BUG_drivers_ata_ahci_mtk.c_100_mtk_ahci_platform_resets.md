# REAL BUG: drivers/ata/ahci_mtk.c:100 mtk_ahci_platform_resets()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L95  | error (deassert axi fail) | YES (reg, sw succeeded) | NO (missing assert) | ❌ LEAK | reg_rst & sw_rst deassert refs leaked |

## Full Response

```
| Line | Return Type | GET Done? (deassert) | PUT Done? (assert) | Balanced? | Notes |
|------|-------------|----------------------|--------------------|-----------|-------|
| L52  | error (EPROBE_DEFER) | NO (before deassert) | N/A | ✅ | no deassert yet |
| L56  | error (EPROBE_DEFER) | NO (before deassert) | N/A | ✅ | |
| L60  | error (EPROBE_DEFER) | NO (before deassert) | N/A | ✅ | |
| L65  | error (assert axi fail) | NO (before deassert) | N/A | ✅ | no deassert yet |
| L71  | error (assert sw fail) | NO (before deassert) | N/A | ✅ | |
| L77  | error (assert reg fail) | NO (before deassert) | N/A | ✅ | |
| L83  | error (deassert reg fail) | NO (deassert failed) | N/A | ✅ | no prior deasserts succeeded |
| L89  | error (deassert sw fail) | YES (reg succeeded) | NO (missing assert) | ❌ LEAK | reg_rst deassert ref leaked |
| L95  | error (deassert axi fail) | YES (reg, sw succeeded) | NO (missing assert) | ❌ LEAK | reg_rst & sw_rst deassert refs leaked |
| L98  | success | YES (all three) | N/A (balanced by later driver lifecycle) | ✅ | lifetime managed by remove/suspend |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_deassert()` on `reg_rst` and `sw_rst` succeeds, but subsequent `deassert()` failures return without calling `reset_control_assert()` to undo those gets.
```
