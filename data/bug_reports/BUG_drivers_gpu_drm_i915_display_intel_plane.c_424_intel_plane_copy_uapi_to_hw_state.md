# REAL BUG: drivers/gpu/drm/i915/display/intel_plane.c:424 intel_plane_copy_uapi_to_hw_state()

**Confidence**: HIGH | **Counter**: `plane_state->hw.fb->base.refcount.refcount.refs.counter`

## Reasoning

| L424 | implicit return (void) | YES (if hw.fb non-null) | YES (old fb’s ref released in `intel_plane_clear_hw_state` at start) | ❌ unsafe order | `put` on old fb happens **before** `get` on new fb. If old == new, refcount can drop to 0, causing a use-after-free. |

## Full Response

```
| Line | Return Type | GET Done?        | PUT Done?             | Balanced? | Notes                                                                                   |
|------|-------------|------------------|-----------------------|-----------|-----------------------------------------------------------------------------------------|
| L424 | implicit return (void) | YES (if hw.fb non-null) | YES (old fb’s ref released in `intel_plane_clear_hw_state` at start) | ❌ unsafe order | `put` on old fb happens **before** `get` on new fb. If old == new, refcount can drop to 0, causing a use-after-free. |

VERDICT: REAL_BUG

CONFIDENCE: HIGH

`intel_plane_clear_hw_state()` puts the old fb reference before `drm_framebuffer_get()` acquires the new one. If `from_plane_state->uapi.fb` matches the current `plane_state->hw.fb`, the refcount may reach zero between the put and the get, leading to a freed fb pointer being reaccessed. Reorder to get before put.
```
