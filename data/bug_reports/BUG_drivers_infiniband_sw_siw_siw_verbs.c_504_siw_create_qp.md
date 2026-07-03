# REAL BUG: drivers/infiniband/sw/siw/siw_verbs.c:504 siw_create_qp()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L432 | `return 0` (success) | YES | NO (held for lifetime) | ✅ | released on QP destruction |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L322 | `return -EOPNOTSUPP` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L327 | `goto err_atomic` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L332 | `goto err_atomic` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L337 | `goto err_atomic` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L343 | `goto err_atomic` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L348 | `goto err_atomic` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L353 | `goto err_atomic` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L358 | `goto err_atomic` | NO (before `siw_qp_add`) | N/A | ✅ | |
| L363‑364 | `if (rv) goto err_atomic` | NO (`siw_qp_add` failed) | N/A | ✅ | get not executed |
| L377 | `goto err_out_xa` (`sendq==NULL`) | YES | NO | ❌ LEAK | `err_out_xa` has no `kref_put` |
| L383 | `goto err_out_xa` (`sq_sig_type`) | YES | NO | ❌ LEAK | |
| L395 | `goto err_out_xa` (`recvq==NULL`) | YES | NO | ❌ LEAK | |
| L406 | `goto err_out_xa` (`!sq_entry`) | YES | NO | ❌ LEAK | |
| L414 | `goto err_out_xa` (`!rq_entry`) | YES | NO | ❌ LEAK | |
| L419 | `goto err_out_xa` (`outlen` too small) | YES | NO | ❌ LEAK | |
| L423 | `goto err_out_xa` (`ib_copy_to_udata` fail) | YES | NO | ❌ LEAK | |
| L425‑427 | `goto err_out_xa` (`tx_cpu<0`) | YES | NO | ❌ LEAK | |
| L432 | `return 0` (success) | YES | NO (held for lifetime) | ✅ | released on QP destruction |

## VERDICT: REAL_BUG
CONFIDENCE: HIGH

`siw_qp_add()` initialises the QP’s kref (contract shows `kref_init`), creating an initial reference. All error paths after that call and before the final `list_add_tail` jump to `err_out_xa`, which only does `xa_erase`, removes mmap entries, and frees buffers – none of which release the kref. Therefore, every such error path leaks the reference, causing the inconsistent refcounting warning.
```
