# REAL BUG: drivers/media/cec/platform/meson/ao-cec.c:696 meson_ao_cec_probe()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L683 | return 0 (success) | YES | NO (deferred to remove) | ✅ | ref held for device lifetime |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L610 | error return | NO (before get) | N/A | ✅ | |
| L614 | error return | NO (before get) | N/A | ✅ | |
| L624 | error return | NO (before get) | N/A | ✅ | |
| L631 | goto out_probe_adapter | NO (before get) | N/A | ✅ | Only adapter cleanup |
| L641 | goto out_probe_adapter | NO (before get) | N/A | ✅ | |
| L648 | goto out_probe_adapter | NO (before get) | N/A | ✅ | |
| L654 | goto out_probe_adapter | NO (before get) | N/A | ✅ | |
| L660 | goto out_probe_clk | NO (before get) | N/A | ✅ | clk disable then adapter delete |
| L672 | goto out_probe_clk | NO (get failed: !notify) | N/A | ✅ | no ref taken, only clk+adapter cleanup |
| L677 | goto out_probe_notify | YES (notify non‑NULL) | YES (cec_notifier_cec_adap_unregister at L686) then likely extra PUT inside `cec_delete_adapter` at L692 | ❌ EXCESS PUT | unregister already releases the notifier; if `cec_delete_adapter` also calls notifier put, refcount goes negative |
| L683 | return 0 (success) | YES | NO (deferred to remove) | ✅ | ref held for device lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error path after `cec_register_adapter` failure calls `cec_notifier_cec_adap_unregister` (L686) then falls through to `cec_delete_adapter` (L692) which likely performs another notifier put, leading to the reported excess put.
```
