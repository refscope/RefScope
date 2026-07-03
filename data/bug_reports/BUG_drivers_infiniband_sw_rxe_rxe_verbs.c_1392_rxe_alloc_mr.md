# REAL BUG: drivers/infiniband/sw/rxe/rxe_verbs.c:1392 rxe_alloc_mr()

**Confidence**: HIGH | **Counter**: `$->ref_cnt.refcount.refs.counter`

## Reasoning

| L1381 | success | YES (pool reference) | N/A (ownership transferred) | ✅ | normal success path, ref held appropriately |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1358 (goto err_out) | error (-EINVAL) | NO (before any get) | N/A | ✅ | mr_type invalid, no allocation |
| L1365 | error (-ENOMEM) | NO (allocation failed) | N/A | ✅ | mr == NULL |
| L1368→err_free | error (rxe_add_to_pool fails) | YES (unconditional kref_init in rxe_add_to_pool) | NO (err_free only kfree, no rxe_cleanup) | ❌ LEAK | refcount set to 1 but never released, memory freed with ref held |
| L1375→err_cleanup→err_free | error (rxe_mr_init_fast fails) | YES | YES (rxe_cleanup unconditionally puts) | ✅ | rxe_cleanup called to release ref before kfree |
| L1381 | success | YES (pool reference) | N/A (ownership transferred) | ✅ | normal success path, ref held appropriately |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rxe_add_to_pool` unconditionally initializes the kref (GET=1). On its error path (L1368→err_free) the code calls `kfree(mr)` without first releasing the reference via `rxe_cleanup`, leaving the refcount dangling and leaking the reference.
```
