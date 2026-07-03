# REAL BUG: drivers/gpu/drm/drm_framebuffer.c:505 drm_mode_closefb_ioctl()

**Confidence**: HIGH | **Counter**: `fb->base.refcount.refcount.refs.counter`

## Reasoning

_closefb`, that call already drops the reference (per contract) → the unconditional `drm_framebuffer_put(fb)` at L505 causes an **excess put**. On error, closefb does **not** drop the ref, so the put is correct. The function lacks conditional put for the success path, leading to a double put. |  |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L492 | error (-EOPNOTSUPP) | NO (before get) | N/A | ✅ | feature check fails |
| L494 | error (-EINVAL) | NO (before get) | N/A | ✅ | pad validation fails |
| L498 | error (-ENOENT) | NO (lookup returned NULL) | N/A | ✅ | conditional get failed |
| L505 | error (ret < 0) | YES (lookup succeeded) | YES (unconditional put) | ⚠️ On **success** of `drm_mode_closefb`, that call already drops the reference (per contract) → the unconditional `drm_framebuffer_put(fb)` at L505 causes an **excess put**. On error, closefb does **not** drop the ref, so the put is correct. The function lacks conditional put for the success path, leading to a double put. |  |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`drm_mode_closefb` already drops the reference on success (contract), but `drm_mode_closefb_ioctl()` unconditionally calls `drm_framebuffer_put(fb)` afterward, causing an excess put when closefb returns 0.
```
