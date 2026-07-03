# REAL BUG: drivers/infiniband/sw/rxe/rxe_verbs.c:1311 rxe_reg_user_mr()

**Confidence**: HIGH | **Counter**: `$->ref_cnt.refcount.refs.counter`

## Reasoning

| L1295 → err_cleanup | error (goto) | YES | YES | ✅ | `rxe_cleanup` calls `__rxe_put` |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1265 | error       | NO (before get) | N/A  | ✅ | dmah=non-NULL, mr not allocated |
| L1269 | error       | NO (before get) | N/A  | ✅ | unsupported access mask |
| L1274 | error       | NO (before get) | N/A  | ✅ | kzalloc failure |
| L1279 → err_free | error (goto) | YES | NO | ❌ LEAK | `rxe_add_to_pool` unconditional kref_init, no put before kfree |
| L1295 → err_cleanup | error (goto) | YES | YES | ✅ | `rxe_cleanup` calls `__rxe_put` |
| L1300 | success     | YES | N/A (ownership transfer) | ✅ | ref held by caller/pool |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rxe_add_to_pool` unconditionally calls `kref_init`, so even when it returns an error the `mr->ref_cnt` is initialized. The `err_free` path (`goto err_free` after add failure) does `kfree(mr)` without a matching `kref_put` (e.g., via `rxe_cleanup`), leaking the initialized refcount.
```
