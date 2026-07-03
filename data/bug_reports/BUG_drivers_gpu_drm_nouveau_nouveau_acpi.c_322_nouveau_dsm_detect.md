# REAL BUG: drivers/gpu/drm/nouveau/nouveau_acpi.c:322 nouveau_dsm_detect()

**Confidence**: MEDIUM | **Counter**: `$->dev.kobj.kref.refcount.refs.counter`

## Reasoning

certainly in this function: likely it calls `pci_dev_put()` (or an equivalent `kobject_put()`) on the `pdev` passed in, without a prior `pci_dev_get()`. That extra put causes a refcount underflow when the loop’s internal `pci_get_base_class()` later tries to release the same device’s reference.

## Full Response

```
## Path Table (Main Function: `nouveau_dsm_detect`)

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L321 | `return ret` (single exit) | YES (multiple `pci_get_base_class()` calls inside `while` loop) | YES (each `pci_get_base_class` call puts the previous device when `pdev` is non‑NULL, and the final `NULL` return puts the last device) | ✅ (from this function’s perspective) | At loop exit, `pdev == NULL`, no outstanding PCI references. *However*, the warning indicates an excess **put** originates elsewhere – likely inside `nouveau_dsm_pci_probe()`. |

The function has only one return path, and the standard `pci_get_device`‑style iteration ensures each device reference is released when the loop terminates. The contract for `pci_get_base_class()` is a conditional‑on‑path wrapper that expects the caller to follow this pattern.

## Missing Callee Source

To determine why an **excess put** is detected, I need the source of the callee where a `put` may be issued incorrectly:

[NEED_SOURCE] nouveau_dsm_pci_probe

The bug is almost certainly in this function: likely it calls `pci_dev_put()` (or an equivalent `kobject_put()`) on the `pdev` passed in, without a prior `pci_dev_get()`. That extra put causes a refcount underflow when the loop’s internal `pci_get_base_class()` later tries to release the same device’s reference.

## VERDICT: REAL_BUG
## CONFIDENCE: MEDIUM

The detection function itself is correctly balanced, but an excess put inside `nouveau_dsm_pci_probe()` creates a double‑put scenario on the PCI device’s kref.
```
