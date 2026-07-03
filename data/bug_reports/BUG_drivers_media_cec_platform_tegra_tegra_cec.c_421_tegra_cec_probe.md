# REAL BUG: drivers/media/cec/platform/tegra/tegra_cec.c:421 tegra_cec_probe()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L405 return 0 | success | CONDITIONAL | NO (held for device lifetime) | ⚠️ success holds ref, later put expected; not the excess here | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L324 | error (IS_ERR(hdmi_dev)) | NO (before get) | N/A | ✅ | |
| L329 | error (!cec) | NO | N/A | ✅ | |
| L335 | error (!res) | NO | N/A | ✅ | |
| L341 | error (!devm_request_mem_region) | NO | N/A | ✅ | |
| L346 | error (cec->tegra_cec_irq < 0) | NO | N/A | ✅ | |
| L354 | error (!cec->cec_base) | NO | N/A | ✅ | |
| L361 | error (IS_ERR_OR_NULL(clk)) | NO | N/A | ✅ | |
| L366 | error (clk_prepare_enable fail) | NO | N/A | ✅ | |
| L379 goto err_clk | error (irq request fail) | NO (no get) | N/A | ✅ | clk prepared, disabled in err_clk |
| L390 goto err_clk | error (adapter alloc fail) | NO (no get) | N/A | ✅ | |
| L396 goto err_adapter | error (notifier NULL) | NO (get returned NULL) | N/A | ✅ | notifier NULL, no put |
| L401 goto err_notifier | error (register adapter fail) | **CONDITIONAL** – may be NO | **YES** (unconditional via unregister) | ❌ EXCESS PUT | if get path didn’t inc ref, unregister’s put causes underflow |
| L405 return 0 | success | CONDITIONAL | NO (held for device lifetime) | ⚠️ success holds ref, later put expected; not the excess here | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`cec_notifier_cec_adap_register` has `conditional_on_path` GET, so non‑NULL return does not guarantee a reference was taken; the error path at L401 then blindly calls `cec_notifier_cec_adap_unregister` (which unconditionally puts), risking an excess put on the notifier’s kref.
```
