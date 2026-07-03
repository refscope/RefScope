# REAL BUG: drivers/gpu/drm/bridge/synopsys/dw-hdmi-cec.c:304 dw_hdmi_cec_probe()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L304 | 0 (success) | YES | NO (put deferred to adapter lifetime) | ✅ | Ownership transferred; notifier released when adapter is unregistered, no local put needed. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L241 | -ENXIO      | NO (before get) | N/A | ✅ | Early error, no get |
| L247 | -ENOMEM     | NO (before get) | N/A | ✅ | Alloc failure |
| L263 | PTR_ERR(adap) | NO (before get) | N/A | ✅ | Adapter alloc failure |
| L269 | ret (action fail) | NO (before get) | N/A | ✅ | devm_add_action_or_reset error |
| L275 | ret (irq fail) | NO (before get) | N/A | ✅ | IRQ request failure |
| L282 | -ENOMEM     | NO (get returned NULL) | N/A | ✅ | Notifier get failed |
| L289 (error) | ret        | YES | YES (manual unregister) | ⚠️ Balanced locally, but **grossly unbalanced** globally | After this path returns, the devm action `dw_hdmi_cec_del` will call `cec_delete_adapter`, which calls `cec_notifier_cec_adap_unregister` again, resulting in double put. This is the excess put reported. |
| L304 | 0 (success) | YES | NO (put deferred to adapter lifetime) | ✅ | Ownership transferred; notifier released when adapter is unregistered, no local put needed. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The error path after `cec_register_adapter()` manually calls `cec_notifier_cec_adap_unregister()`, but the devm action `dw_hdmi_cec_del` will later call `cec_delete_adapter()`, which itself releases the notifier through the CEC framework, causing a double put (excess). Removing the manual unregister in the error handler restores balance.
```
