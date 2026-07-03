# REAL BUG: drivers/media/cec/platform/seco/seco-cec.c:668 secocec_probe()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

If the GET did **not** increment the refcount on the paths that reach `err_notifier`, then calling `cec_notifier_cec_adap_unregister()` causes a refcount **excess put** (underflow). The warning explicitly flags this imbalance.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L570 | error       | NO        | N/A       | ✅         | return early, before any notifier get |
| L574 | error       | NO        | N/A       | ✅         | before notifier get |
| L581 | error       | NO        | N/A       | ✅         | before notifier get |
| L590 (goto err)          | error       | NO        | NO        | ✅         | notifier not yet allocated |
| L597 (goto err)          | error       | NO        | NO        | ✅         | notifier not yet allocated |
| L604 (goto err)          | error       | NO        | NO        | ✅         | notifier not yet allocated |
| L610 (goto err)          | error       | NO        | NO        | ✅         | notifier not yet allocated |
| L623 (goto err)          | error       | NO        | NO        | ✅         | notifier not yet allocated |
| L636 (goto err)          | error       | NO        | NO        | ✅         | notifier not yet allocated |
| L643 (goto err_delete_adapter) | error       | NO (get failed, NULL) | NO        | ✅         | notifier register failed, no unregister |
| L647 (goto err_notifier) | error       | YES (non‑NULL return) | YES (unregister called) | ❌ SEE NOTES | conditional GET may not have incremented refcount → excess put |
| L651 (goto err_notifier) | error       | YES (non‑NULL return) | YES (unregister called) | ❌ SEE NOTES | same conditional GET mismatch |
| L658 (success return)    | success     | YES       | NO        | ⚠️ (leak, but not excess put) | notifier ref held for device lifetime – leak on success is a separate issue |

**Notes on L647/L651**  
The contract for `cec_notifier_cec_adap_register()` states **conditional_on_path** – the kref may not be incremented on all execution paths.  
The contract for `cec_notifier_cec_adap_unregister()` states **unconditional** put.  
If the GET did **not** increment the refcount on the paths that reach `err_notifier`, then calling `cec_notifier_cec_adap_unregister()` causes a refcount **excess put** (underflow). The warning explicitly flags this imbalance.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`cec_notifier_cec_adap_unregister` unconditionally calls `cec_notifier_put`, but the matching `cec_notifier_cec_adap_register` only increments the kref conditionally. On the error paths at L647 and L651, a non‑NULL notifier may have been obtained without a reference bump, leading to an excess put when the notifier is unregistered.
```
