# REAL BUG: drivers/usb/gadget/function/f_ecm.c:457 ecm_notify_complete()

**Confidence**: HIGH | **Counter**: `ecm->notify_count.counter`

## Reasoning

All paths proceed to the call `ecm_do_notify(ecm)` which (based on naming and typical pattern) increments `notify_count` (the GET). The `default` path decrements the counter without checking its current value, making it possible to dec when the counter is zero.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 441 (status == 0)            | fall‑through (implicit return at end) | YES (ecm_do_notify after switch) | YES (atomic_dec) | ✅ | dec on positive ref, inc after restores balance |
| 444‑446 (status -ECONNRESET or -ESHUTDOWN) | fall‑through    | YES (ecm_do_notify after switch) | NO (atomic_set not a put) | ✅ | ref set to 0 (no dec), then inc makes 1 – no excess put |
| 449‑452 (default, other error)  | fall‑through    | YES (ecm_do_notify after switch) | YES (atomic_dec) | ❌ **EXCESS PUT** | atomic_dec called unconditionally; if ref is already 0 (e.g. after prior shutdown) it underflows, causing the reported excess put |

All paths proceed to the call `ecm_do_notify(ecm)` which (based on naming and typical pattern) increments `notify_count` (the GET). The `default` path decrements the counter without checking its current value, making it possible to dec when the counter is zero.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The default error handler unconditionally calls `atomic_dec`, but the refcount can be zero (e.g. after a reset/shutdown that set it to zero). This leads to an atomic underflow, matching the “excess put” report. The nearby `-ECONNRESET`/`-ESHUTDOWN` case explicitly resets the count to zero to avoid this, indicating the default path is missing a similar guard.
```
