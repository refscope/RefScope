# REAL BUG: drivers/gpu/drm/i915/i915_cmd_parser.c:1233 copy_batch()

**Confidence**: HIGH | **Counter**: `$->mm.pages_pin_count.counter`

## Reasoning

| L1230 (success, pin_map never called) | success | NO (condition false) | YES (finis_access) | ❌ LEAK (excess put) | get never happened, but finis_access does a put |

## Full Response

```
[NEED_SOURCE] i915_gem_object_finish_access

| Line | Return Type | GET Done? (src_obj pages_pin) | PUT Done? (src_obj pages_pin) | Balanced? | Notes |
|------|-------------|-------------------------------|-------------------------------|-----------|-------|
| L1166 | error (prepare_write fail) | NO (before any src get) | N/A | ✅ | |
| L1171 | error (IS_ERR(dst)) | NO (before src get) | N/A | ✅ | |
| L1176 | error (prepare_read fail) | NO (only dst unpin) | N/A | ✅ | |
| L1230 (success, pin_map(src) succeeded) | success | YES (pin_map at L1181) | YES (unpin_map at L1186) + YES (finis_access at ~L1233) | ❌ LEAK (excess put) | pin_map>0, unpin_map balances it; finis_access does an extra put on pages_pin_count |
| L1230 (success, pin_map(src) failed) | success | NO (pin_map returned ERR) | YES (finis_access) | ❌ LEAK (excess put) | get never happened, but finis_access does a put |
| L1230 (success, pin_map never called) | success | NO (condition false) | YES (finis_access) | ❌ LEAK (excess put) | get never happened, but finis_access does a put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`i915_gem_object_finish_access(src_obj)` (line 1233) unconditionally releases a pages_pin_count reference, but `src_obj` is only pinned via `pin_map` in one conditional path (and immediately unpinned); all other paths reach the same `finish_access` with no prior pin, causing an excess put on `$->mm.pages_pin_count.counter`.
```
