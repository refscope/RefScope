# REAL BUG: drivers/gpu/drm/drm_plane.c:1577 drm_mode_page_flip_ioctl()

**Confidence**: HIGH | **Counter**: `$->base.refcount.refcount.refs.counter`

## Reasoning

| **Callback succeeds, `plane->state != NULL`** | success | YES | `fb` put + `plane->old_fb` put | ❌ **EXCESS PUT** | Atomic callback already released old ref; this extra put on `plane->old_fb` triggers warning |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1390-L1412, etc. (early checks) | error returns | NO (fb=NULL) | NO (out not reached) | ✅ | No framebuffer involved |
| old_fb == NULL → `goto out` | error (-EBUSY) | NO (fb=NULL) | NO (plane->old_fb not set) | ✅ | |
| `fb == NULL` → `goto out` | error (-ENOENT) | NO (fb=NULL) | NO | ✅ | |
| Format/coords errors → `goto out` (after `fb` lookup) | error | YES (fb non-NULL) | `fb` put only | ✅ | `plane->old_fb` not set yet |
| Event allocation failure → `goto out` | error | YES | `fb` put only | ✅ | |
| Callback fails, `plane->old_fb = NULL` → fall to `out` | error | YES | `fb` put only (old_fb=NULL) | ✅ | old_fb kept by `plane->fb` |
| Callback succeeds, `plane->state == NULL` | success | YES + extra `drm_framebuffer_get(fb)` | `fb` put + `plane->old_fb` put | ✅ | Legacy path: old ref released, new ref taken |
| **Callback succeeds, `plane->state != NULL`** | success | YES | `fb` put + `plane->old_fb` put | ❌ **EXCESS PUT** | Atomic callback already released old ref; this extra put on `plane->old_fb` triggers warning |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On successful atomic page flip, the `out` label unconditionally calls `drm_framebuffer_put(plane->old_fb)`, but the callback has already released that reference, causing a refcount excess put at the old framebuffer.
```
