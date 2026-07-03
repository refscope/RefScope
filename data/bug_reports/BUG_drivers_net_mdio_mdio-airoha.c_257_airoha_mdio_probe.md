# REAL BUG: drivers/net/mdio/mdio-airoha.c:257 airoha_mdio_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L243 (return 0) | success     | YES       | NO (held for device lifetime) | ✅ | Probe success leaves reset deasserted; remove() will assert |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L207 (of_property_read_u32 fail) | error       | NO        | N/A       | ✅ | before reset_control_deassert |
| L211 (devm_mdiobus_alloc_size fail) | error       | NO        | N/A       | ✅ | before reset_control_deassert |
| L215 (regmap IS_ERR) | error       | NO        | N/A       | ✅ | before reset_control_deassert |
| L219 (clk IS_ERR) | error       | NO        | N/A       | ✅ | before reset_control_deassert |
| L223 (priv->reset IS_ERR) | error       | NO        | N/A       | ✅ | before reset_control_deassert |
| L236 (clk_set_rate fail) | error       | YES       | NO        | ❌ LEAK | Missing reset_control_assert() |
| L241 (devm_of_mdiobus_register fail) | error       | YES       | YES       | ✅ | Explicit assert before return |
| L243 (return 0) | success     | YES       | NO (held for device lifetime) | ✅ | Probe success leaves reset deasserted; remove() will assert |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`clk_set_rate()` failure at L236 returns directly without calling `reset_control_assert()`, leaking the deassert reference acquired unconditionally at L225.
```
