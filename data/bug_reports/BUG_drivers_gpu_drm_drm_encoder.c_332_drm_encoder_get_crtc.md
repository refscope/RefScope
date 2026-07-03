# REAL BUG: drivers/gpu/drm/drm_encoder.c:332 drm_encoder_get_crtc()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

| after loop → L329 (if !uses_atomic) return encoder->crtc | returns crtc | same | same | ❌ EXCESS PUT | Same double-put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L320 (inside loop, after iter_end) | success | YES (connector matched) | YES (iter_end releases that one) | ✅ | Correct: releases the currently held connector |
| after loop → L326 (if uses_atomic) return NULL | returns NULL | YES (last connector ref acquired, then released by final `drm_connector_list_iter_next`) | YES (iter_end is called, but that last connector’s ref was already released) | ❌ EXCESS PUT | Double-put: the final `next` call already dropped the last connector’s reference; `iter_end` drops it again |
| after loop → L329 (if !uses_atomic) return encoder->crtc | returns crtc | same | same | ❌ EXCESS PUT | Same double-put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The after-loop `drm_connector_list_iter_end()` double-releases the last connector because `drm_connector_list_iter_next()` already dropped its reference when the loop terminated. The early-return path is safe, but the normal loop-exit paths trigger an excess put, as smatch detected.
```
