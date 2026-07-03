# REAL BUG: drivers/infiniband/sw/rxe/rxe_verbs.c:600 rxe_create_qp()

**Confidence**: HIGH | **Counter**: `$->ref_cnt.refcount.refs.counter`

## Reasoning

| L592 | return 0 (success) | YES (pool add succeeded) | DECOUPLED (held for object lifetime; destroy_qp will put) | ✅ | |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L548 | goto err_out | NO (before rxe_add_to_pool) | N/A | ✅ | |
| L554 | goto err_out | NO | N/A | ✅ | |
| L565 | goto err_out | NO | N/A | ✅ | |
| L571 | goto err_out | NO | N/A | ✅ | |
| L578 | goto err_out (rxe_add_to_pool fails) | YES (unconditional GET per contract) | NO (err_out has no rxe_cleanup) | ❌ LEAK | rxe_add_to_pool did kref_init; error path skips put |
| L588 | goto err_cleanup | YES (pool add succeeded) | YES (rxe_cleanup) | ✅ | |
| L592 | return 0 (success) | YES (pool add succeeded) | DECOUPLED (held for object lifetime; destroy_qp will put) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rxe_add_to_pool` (contract says unconditional GET, sets refcount via kref_init) failure path at L578 falls through to `err_out`, which does not call `rxe_cleanup`; this leaks the initial reference.
```
```
