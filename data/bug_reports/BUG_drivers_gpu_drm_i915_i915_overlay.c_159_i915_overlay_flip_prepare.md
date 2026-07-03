# REAL BUG: drivers/gpu/drm/i915/i915_overlay.c:159 i915_overlay_flip_prepare()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| end (L163) | void return | YES (if vma != NULL) | YES (if overlay->frontbuffer != NULL) | **NO** | `i915_gem_object_frontbuffer_track()` already puts the old frontbuffer; explicit `put` afterwards is an extra decrement → double‑put |

## Full Response

```
[NEED_SOURCE] i915_gem_object_frontbuffer_track

| Line      | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|-----------|-------------|-----------|-----------|-----------|-------|
| end (L163) | void return | YES (if vma != NULL) | YES (if overlay->frontbuffer != NULL) | **NO** | `i915_gem_object_frontbuffer_track()` already puts the old frontbuffer; explicit `put` afterwards is an extra decrement → double‑put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`i915_gem_object_frontbuffer_track()` internally releases the old frontbuffer reference, so the later `i915_gem_object_frontbuffer_put(overlay->frontbuffer)` is a redundant put, causing a refcount underflow (excess put).
```
