# REAL BUG: drivers/acpi/acpi_platform.c:67 acpi_platform_device_remove_notify()

**Confidence**: HIGH | **Counter**: `pdev->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L67 (return NOTIFY_OK) | final return | not executed on its own; all paths lead here | — | — | Final return reached through one of the above paths |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L53 (break from ADD) | fallthrough to L67 | NO (before get) | N/A | ✅ | Not REMOVE case |
| L56 (break from REMOVE, !enumerated) | fallthrough to L67 | NO (before get) | N/A | ✅ | |
| L60 (break from REMOVE, pdev==NULL) | fallthrough to L67 | YES → NO (pdev NULL, get failed) | N/A | ✅ | Conditional GET, pdev==NULL means no ref taken |
| L64 (break after unregister + put) | fallthrough to L67 | YES (pdev non‑NULL) | YES×2 (unregister’s platform_device_put + explicit put_device) | ❌ EXCESS PUT | One get, two puts → refcount underflow |
| L67 (return NOTIFY_OK) | final return | not executed on its own; all paths lead here | — | — | Final return reached through one of the above paths |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`platform_device_unregister()` already calls `platform_device_put()` → `put_device()`; the extra `put_device(&pdev->dev)` at line 63 double‑puts the reference acquired by `acpi_platform_device_find_by_companion()`, triggering the excess‑put warning.
```
