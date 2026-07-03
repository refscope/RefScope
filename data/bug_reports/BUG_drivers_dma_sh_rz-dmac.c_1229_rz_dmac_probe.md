# REAL BUG: drivers/dma/sh/rz-dmac.c:1229 rz_dmac_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| ~L1231 (success) | return 0 | YES | NO (held for device lifetime) | ✅ | device keeps reference; no leak on success |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1103 (NULL kzalloc) | error (-ENOMEM) | NO (before get) | N/A | ✅ | reset_control_deassert not called |
| ~L1110 (rz_dmac_parse_of fail) | error (ret) | NO | N/A | ✅ | |
| ~L1115 (kcalloc fail) | error (-ENOMEM) | NO | N/A | ✅ | |
| ~L1120 (ioremap base fail) | error (PTR_ERR) | NO | N/A | ✅ | |
| ~L1125 (ext_base fail) | error (PTR_ERR) | NO | N/A | ✅ | |
| ~L1132 (request_irq fail) | error (ret) | NO | N/A | ✅ | |
| ~L1139 (reset get fail) | error (dev_err_probe) | NO | N/A | ✅ | |
| ~L1153 (pm_runtime_resume fail) | goto err_pm_disable | NO (before get) | N/A | ✅ | deassert not yet called |
| **L1229 (deassert fail)** | **goto err_pm_runtime_put** | **YES** | **NO** | ❌ **LEAK** | deassert increments counter (unconditional per contract); error path skips assert |
| ~L1178‑L1182 (channel probe error) | goto err | YES (deassert ok) | YES (err does assert) | ✅ | err label includes reset_control_assert |
| ~L1188 (of_dma fail) | goto err | YES | YES | ✅ | err includes assert |
| ~L1224 (dma_async_register fail) | goto dma_register_err → falls to err | YES | YES | ✅ | after of_dma_controller_free, err includes assert |
| ~L1231 (success) | return 0 | YES | NO (held for device lifetime) | ✅ | device keeps reference; no leak on success |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the error path where `reset_control_deassert()` fails (ret != 0) at L1229, the code jumps to `err_pm_runtime_put` which does **not** call `reset_control_assert()`. According to the provided contract, `reset_control_deassert()` unconditionally increments the deassert_count, so this path leaves an excess reference on `deassert_count`.
```
