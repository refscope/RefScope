# REAL BUG: drivers/gpu/drm/ttm/tests/ttm_bo_validate_test.c:1117 ttm_bo_validate_evict_gutting()

**Confidence**: LOW | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

- Without the source of `ttm_bo_init_reserved`, we cannot confirm whether the reference is held on error. Therefore the exact balance of the `err != 0` path remains **uncertain**.

## Full Response

```
```
| Line  | Return Type     | GET Done?                         | PUT Done?       | Balanced? | Notes                                                                                                                                                                          |
|-------|------------------|-----------------------------------|-----------------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L1092 | KUNIT_ASSERT     | NO (bo_evict uninitialized, no GET yet) | N/A             | ✅        | bo_evict == NULL, no ref acquired.                                                                                                                                             |
| L1095 | err != 0 (non‑abort) |**UNCERTAIN**: GET by ttm_bo_init_reserved is unconditional but on error the function may call ttm_bo_put internally, releasing the ref. If it does NOT, caller still holds ref. | PUT at L1113 executed | ⚠️        | **Excess put if ttm_bo_init_reserved releases ref on error.** If not, balanced.                                                                                                   |
| L1095 | err == 0 (success) | YES (ref held, refcount=1)        | PUT at L1113     | ✅        | Normal success: one get, one put.                                                                                                                                              |
| L1110 | KUNIT_ASSERT     | YES (bo_evict already gotten; bo also gotten) | NONE            | ❌ LEAK   | Both bo_evict and bo references leaked (missed ttm_bo_fini). Not the warned excess-put issue.                                                                                   |
| L1111 | KUNIT_ASSERT     | YES                               | NONE            | ❌ LEAK   | Same as L1110, leak.                                                                                                                                                           |
| L1117 | normal exit      | YES (success path)                | PUT at L1113, L1114 | ✅        | All puts performed on success path.                                                                                                                                            |

[NEED_SOURCE] ttm_bo_init_reserved

**Notes**:
- The warning is **“refcount excess put”** on `$->kref.refcount.refs.counter` at line 1117, triggered by smatch.
- The only plausible cause is the **error path of ttm_bo_init_reserved** at L1095: if `err != 0` and the function **internally releases the reference** (by calling `ttm_bo_put`), then the unconditional `ttm_bo_fini(bo_evict)` at L1113 becomes an **extra decrement** → excess put.
- The contract for `ttm_bo_init_reserved` lists `→ttm_bo_put(put),kref_init(set)`, suggesting it uses both `kref_init` (set to 1) and `ttm_bo_put` (decrement) internally. That is **consistent with an erro
```
