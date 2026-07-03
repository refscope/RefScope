# REAL BUG: drivers/gpu/drm/xe/xe_svm.c:1120 xe_drm_pagemap_populate_mm()

**Confidence**: HIGH | **Counter**: `$->ttm.base.refcount.refcount.refs.counter`

## Reasoning

The retry path discards a successfully created ` xe_bo` without releasing its initial reference, leaking the `ttm.base.refcount` counter that SMatch monitors.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1064 | error return | NO (no bo) | N/A | ✅ | `drm_dev_enter` fails, return -ENODEV |
| ~L1072 | implicit retry (goto/continue) inside `xe_validation_guard` | NO (xe_bo_get not reached) | NO (missing put on creation ref) | ❌ LEAK | `drm_exec_retry_on_contention` triggers loop restart; bo from `xe_bo_create_locked` (creation ref) is leaked, no `xe_bo_put` before overwrite |
| ~L1078 | break (IS_ERR) | NO (before get) | N/A | ✅ | `xe_bo_create_locked` fails, break to end of guard block |
| ~L1118 | normal exit of guard block | YES (`xe_bo_get` at ~L1112) | YES (`xe_bo_put` at ~L1118) | ✅ | balanced: get then put in same block |

The retry path discards a successfully created ` xe_bo` without releasing its initial reference, leaking the `ttm.base.refcount` counter that SMatch monitors.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`xe_bo_create_locked` returns a bo with a reference; if `drm_exec_retry_on_contention` triggers a loop restart, the old bo is leaked (no matching put), causing a refcount leak on the same counter that SMatch warns about.
```
