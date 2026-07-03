# REAL BUG: drivers/gpu/drm/i915/gt/uc/intel_guc_submission.c:776 __guc_add_request()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L735‑737 (`enabled`), L740 `send_nb` → L758 `return err` | error/success | NO | N/A | ✅ | no get in the enabled branch |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L709 (`return 0`) | early success | NO (before any get) | N/A | ✅ | early exit, no get executed |
| L718 (`return err`) | error (policy init) | NO (before get) | N/A | ✅ | |
| L724 (`goto out` → L758 `return err`) | early skip | NO (before get) | N/A | ✅ | context blocked & not parent |
| L728‑733 (`!enabled`), L740 `err != 0` → L750‑752 put → L758 `return err` | error (first send_nb) | YES (L733) | YES (L752) | ✅ | explicit put on error path |
| L728‑733 (`!enabled`), L740 `err == 0`, no parent (or parent send succeeds) → L758 `return 0` | success | YES (L733) | NO (external callback) | ✅ (async) | ref held for G2H response handler; put done later |
| L728‑733 (`!enabled`), L740 `err == 0`, parent present, L748 second `send_nb` fails (`err != 0`) → L758 `return err` | error (second send_nb) | YES (L733) | **NO** | ❌ LEAK | `intel_context_get` done, but error path skips the `else if (!enabled)` put; async handler not triggered |
| L735‑737 (`enabled`), L740 `send_nb` → L758 `return err` | error/success | NO | N/A | ✅ | no get in the enabled branch |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`intel_context_get` at L733 unconditionally increments the refcount. In the `!enabled` case, when the first `send_nb` succeeds (`err == 0`) but the subsequent parent send fails (L748), control does **not** enter the `else if (!enabled)` block that calls `intel_context_put`. This leaves an unbalanced reference on the `intel_context`, causing a refcount leak.
```
