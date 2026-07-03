# REAL BUG: drivers/media/cec/platform/sti/stih-cec.c:365 stih_cec_probe()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

- goto out between GET and PUT? – The error path (L356) goes to label with explicit PUT, but the GET may not have placed a reference → excess.

## Full Response

```
[NEED_SOURCE] cec_notifier_cec_adap_register
[NEED_SOURCE] cec_notifier_cec_adap_unregister

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L311 | error (return PTR_ERR) | NO (before get) | NO | ✅ | |
| L315 | error (return -ENOMEM) | NO | NO | ✅ | |
| L321 | error (return PTR_ERR) | NO | NO | ✅ | |
| L325 | error (return cec->irq) | NO | NO | ✅ | |
| L331 | error (return ret) | NO | NO | ✅ | after devm_request_threaded_irq |
| L336 | error (return PTR_ERR) | NO | NO | ✅ | after devm_clk_get |
| L345 | error (return ret) | NO | NO | ✅ | cec_allocate_adapter failed |
| L351 (goto err_delete_adapter) | error (goto label) | NO (notifier NULL, no ref) | NO (only adapter delete) | ✅ | get returned NULL, handled |
| L356 (goto err_notifier) | error (goto label) | YES (notifier non‑NULL) | YES (L362 unregister) | ❌ EXCESS PUT | GET is CONDITIONAL (may not increment kref); PUT unconditional → underflow |
| L359 | success (return 0) | YES | NO (held for lifetime) | ✅ | reference managed in remove() |

**Pre-verdict checklist**:
- “Held for device lifetime”? – Success path only, not relevant.
- “Ownership transferred”? – No transfer to devm, no deferred cleanup.
- Unconditional GET? – **No**, contract says conditional_on_path.
- goto out between GET and PUT? – The error path (L356) goes to label with explicit PUT, but the GET may not have placed a reference → excess.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `cec_notifier_cec_adap_register()` is documented as conditional_on_path, meaning it does not always increment the kref. On the `err_notifier` path the probe unconditionally calls `cec_notifier_cec_adap_unregister()`, which unconditionally does a put. If the get did not hold a reference, this causes a refcount underflow (excess put) exactly at the put call site.

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] meson_ao_cec_probe

--- [NEED_SOURCE r2] ---

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L311 | error (return PTR_ERR) | NO (before get) | NO | ✅ | |
| L315 | error (return -ENOMEM) | NO | NO | ✅ | |
| L321 | error (return PTR_ERR) | NO | NO | ✅ | |
| L325 | error (return cec->irq) | NO | NO | ✅ | |
| L331 | error (return ret) | NO | NO | ✅ | after devm_request_threaded_irq |
| L336 | error (return PTR_ERR) | NO | NO | ✅ | after devm_clk_get |
| L345 | error (return ret) | NO | NO | ✅ | cec_allocate_adapter failed |
| L351 (goto err_delete_adapter) | error (goto label) | NO (notifier NULL, no ref) | NO (only adapter delete) | ✅ | get returned NULL, handled |
| L356 (goto err_notifier) | error (goto label) | YES (notifier non‑NULL) | YES (L362 unregister) | ❌ EXCESS PUT | GET is CONDITIONAL (may not increment kref); PUT unconditional → underflow |
| L359 | success (return 0) | YES | NO (held for lifetime) | ✅ | reference managed in remove() |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
T
```
