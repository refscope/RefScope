# REAL BUG: drivers/gpu/drm/gud/gud_pipe.c:657 gud_plane_atomic_update()

**Confidence**: LOW | **Counter**: `$->base.refcount.refcount.refs.counter`

## Reasoning

| L648‑L653 normal exit after damage | success return | `gud_fb_handle_damage` called – may take GET (needs investigation) | NO | N/A | GET for `gdrm->fb` done inside callee; no put needed here. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L632 (put in mode_changed block) → then L641 return (if crtc NULL or drm_dev_enter fails) | early return | Unknown – depends on whether previous `gud_fb_handle_damage` took a reference and stored in `gdrm->fb` | YES (`drm_framebuffer_put(gdrm->fb)` at L632) | **Likely NO** (excess put) | Warning: refcount excess put at L657 indicates the put was not matched by a get. The GET is external, occurring inside `gud_fb_handle_damage` during a previous update. If that callee fails to increment the refcount when assigning `gdrm->fb`, the put here is unbalanced. |
| L641 return (if `!crtc` or `!drm_dev_enter`) – no mode_changed block entered | early return | N/A | NO | N/A | No put, no get. Balanced. |
| L644 `goto out` (if `drm_gem_fb_begin_cpu_access` fails) | error return | N/A | NO | N/A | No `gdrm->fb` operations. Balanced. |
| L648‑L653 normal exit after damage | success return | `gud_fb_handle_damage` called – may take GET (needs investigation) | NO | N/A | GET for `gdrm->fb` done inside callee; no put needed here. |

[NEED_SOURCE] gud_fb_handle_damage

VERDICT: REAL_BUG
CONFIDENCE: LOW
The warning reports an exact refcount‑underflow on `drm_framebuffer_put()` at line 657 (the mode‑changed early‑return path). The only put in this function is for `gdrm->fb`, whose reference is meant to be taken by `gud_fb_handle_damage` on prior updates. Without seeing that callee’s source, the excess‑put strongly suggests it never called `drm_framebuffer_get()` when assigning `gdrm->fb`, leaving the stored pointer without a proper reference and causing this put to trigger a refcount‑underflow — a real bug.
```
