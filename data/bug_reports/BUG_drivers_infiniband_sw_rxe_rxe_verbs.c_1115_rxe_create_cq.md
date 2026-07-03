# REAL BUG: drivers/infiniband/sw/rxe/rxe_verbs.c:1115 rxe_create_cq()

**Confidence**: HIGH | **Counter**: `$->ref_cnt.refcount.refs.counter`

## Reasoning

| `return 0` (success) (~L1106) | success | YES | NO (ownership transfer) | ✅ | caller will destroy |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| `goto err_out` after `udata` outlen check (~L1079) | error | NO (before get) | N/A | ✅ | |
| `goto err_out` after `attr->flags` check (~L1087) | error | NO (before get) | N/A | ✅ | |
| `return -EINVAL` after `cqe > max_cqe` (~L1091) | error | NO (before get) | N/A | ✅ | |
| `goto err_out` after `rxe_add_to_pool` fails (~L1095) | error | YES (unconditional kref_init) | NO | ❌ LEAK | err_out does not call rxe_cleanup |
| `goto err_cleanup` after `rxe_cq_from_init` fails (~L1103) | error | YES | YES (rxe_cleanup) | ✅ | |
| `return 0` (success) (~L1106) | success | YES | NO (ownership transfer) | ✅ | caller will destroy |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rxe_add_to_pool` performs unconditional kref_init; its error path jumps to `err_out` which lacks the required `rxe_cleanup`, leaking the reference.
```
