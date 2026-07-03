# REAL BUG: drivers/gpu/drm/ttm/tests/ttm_bo_validate_test.c:969 ttm_bo_validate_allowed_only_evict()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

normal, init_res error) | end of function | YES (unconditional get by `ttm_bo_init_reserved`) | YES (`ttm_bo_fini`) | ❌ **EXCESS PUT** | On error, `ttm_bo_init_reserved` already calls `ttm_bo_put` internally (see contract → `ttm_bo_put`). The caller then calls `ttm_bo_fini` again → double put |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (bo_pinned) | PUT Done? (bo_pinned) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L927 (ASSERT_NOT_NULL) | early return | NO (bo_pinned is NULL) | N/A | ✅ | |
| L938 (ASSERT_NOT_NULL) | early return | YES (if init_res success) / NO (if init_res failed) | NO | ⚠️ (leak on success, not the warned bug) | Returns before `ttm_bo_fini(bo_pinned)`; warning not triggered |
| L969 (normal, init_res success) | end of function | YES (ref from `ttm_bo_init_reserved`) | YES (`ttm_bo_fini`) | ✅ | |
| L969 (normal, init_res error) | end of function | YES (unconditional get by `ttm_bo_init_reserved`) | YES (`ttm_bo_fini`) | ❌ **EXCESS PUT** | On error, `ttm_bo_init_reserved` already calls `ttm_bo_put` internally (see contract → `ttm_bo_put`). The caller then calls `ttm_bo_fini` again → double put |

## VERDICT: REAL_BUG

## CONFIDENCE: HIGH

`ttm_bo_init_reserved` unconditionally acquires a reference (contract: unconditional GET). On failure it cleans up internally via a hidden `ttm_bo_put`, but the test's non‑fatal `KUNIT_EXPECT_EQ` allows the function to reach `ttm_bo_fini(bo_pinned)` at line 969, causing a second put on the already‑released reference, which triggers `refcount excess put`.
```
