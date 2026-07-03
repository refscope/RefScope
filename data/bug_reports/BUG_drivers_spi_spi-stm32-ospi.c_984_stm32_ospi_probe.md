# REAL BUG: drivers/spi/spi-stm32-ospi.c:984 stm32_ospi_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L984 (final return ret; from err_reset_control path) | error (spi_register_controller fails) | YES (deassert called at L965) | NO (err_reset_control only calls reset_control_release, no assert) | ❌ LEAK | Missing reset_control_assert to balance deassert; leak on this error path |

## Full Response

```
| Line | Return Type | GET Done? (deassert_count inc) | PUT Done? (assert) | Balanced? | Notes |
|------|-------------|--------------------------------|---------------------|-----------|-------|
| L895 | error       | NO (before deassert) | N/A | ✅ | |
| L900 | error       | NO (before deassert) | N/A | ✅ | |
| L913 | error       | NO (before deassert, assuming get_resources does not call deassert) | N/A | ✅ | |
| L940 (goto err_dma_free) | error | NO (deassert not yet called) | N/A | ✅ | dma_setup fails before reset_deassert |
| L978 (return 0) | success | YES (deassert called at L965) | NO (ownership transfer to driver: remove() will assert) | ✅ (acceptable pattern) | No assert here is standard for probe success |
| L984 (final return ret; from err_reset_control path) | error (spi_register_controller fails) | YES (deassert called at L965) | NO (err_reset_control only calls reset_control_release, no assert) | ❌ LEAK | Missing reset_control_assert to balance deassert; leak on this error path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On probe error after `reset_control_deassert()`, `err_reset_control` path fails to call `reset_control_assert()`, leaving `deassert_count` incremented.
```
