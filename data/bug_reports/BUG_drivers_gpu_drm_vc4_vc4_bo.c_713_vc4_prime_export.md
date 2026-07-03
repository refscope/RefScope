# REAL BUG: drivers/gpu/drm/vc4/vc4_bo.c:713 vc4_prime_export()

**Confidence**: HIGH | **Counter**: `$->usecnt.refs.counter`

## Reasoning

| `return dmabuf` (success, ~L713) | success | YES | NO | ❌ LEAK | `usecnt` incremented but never released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| `bo->validated_shader` → `return ERR_PTR(-EINVAL)` (~L695) | error | NO (before `vc4_bo_inc_usecnt`) | N/A | ✅ | GET never called |
| `vc4_bo_inc_usecnt` fails (`ret != 0`) → `return ERR_PTR(ret)` (~L701) | error | NO (conditional GET failed) | N/A | ✅ | `ret` indicates no ref held |
| `drm_gem_prime_export` returns `IS_ERR(dmabuf)` → `vc4_bo_dec_usecnt` + `return dmabuf` (~L707) | error | YES | YES | ✅ | explicit release on export failure |
| `return dmabuf` (success, ~L713) | success | YES | NO | ❌ LEAK | `usecnt` incremented but never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The unconditional success path after `vc4_bo_inc_usecnt()` never calls `vc4_bo_dec_usecnt()`, leaving the usecnt permanently elevated. The comment confirms no cleanup exists for the exported BO’s usecnt.
```
