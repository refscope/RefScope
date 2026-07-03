# REAL BUG: drivers/gpu/drm/drm_vblank.c:1235 drm_vblank_get()

**Confidence**: HIGH | **Counter**: `vblank->refcount.counter`

## Reasoning

| L1227 else branch → L1235 (vblank enabled) | success (ret=0) | YES | NO (intentional) | ✅ (caller’s reference) | Normal get when already enabled. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1218 (return -EINVAL) | error | NO (before get) | N/A | ✅ | Early return before lock. |
| L1221 (return -EINVAL) | error | NO (before get) | N/A | ✅ | Early return before lock. |
| L1226 → L1235 (drm_vblank_enable error) | error | **YES** (atomic_add_return at L1225) | **NO** | ❌ **LEAK** | drm_vblank_enable returns error, ret set, no atomic_dec. |
| L1226 → L1235 (drm_vblank_enable success) | success (ret=0) | **YES** | NO (intentional) | ✅ (caller’s reference) | Normal get when enabling. |
| L1229-1230 → L1235 (atomic_dec + error) | error | YES | **YES** (atomic_dec) | ✅ | Undo increment when vblank disabled. |
| L1227 else branch → L1235 (vblank enabled) | success (ret=0) | YES | NO (intentional) | ✅ (caller’s reference) | Normal get when already enabled. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`drm_vblank_get` fails to undo `atomic_add_return(1, &vblank->refcount)` when `drm_vblank_enable()` returns an error, leaking a refcount.
```
