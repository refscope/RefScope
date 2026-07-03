# REAL BUG: crypto/algapi.c:702 crypto_register_instance()

**Confidence**: HIGH | **Counter**: `$->cra_refcnt.refs.counter`

## Reasoning

| L700 | success (return 0 after larval or NULL path) | YES (crypto_check_alg succeeded) | N/A (ownership transferred to crypto layer via larval/final) | ✅ | Ref now managed by subsystem for later unregistration |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L654 | early error (return err) | NO (crypto_check_alg failed, conditional_on_path → no ref taken) | N/A | ✅ | No ref held |
| L684→L692 | error after unlock (goto unlock → return PTR_ERR(larval)) | YES (crypto_check_alg succeeded → refcount_set on inst->alg) | NO (no crypto_mod_put called) | ❌ LEAK | Error path after successful check, no put on instance’s ref |
| L700 | success (return 0 after larval or NULL path) | YES (crypto_check_alg succeeded) | N/A (ownership transferred to crypto layer via larval/final) | ✅ | Ref now managed by subsystem for later unregistration |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`crypto_check_alg` succeeds and takes a reference on `inst->alg`, but when `__crypto_register_alg` fails (returns ERR_PTR) the function returns without releasing that reference, causing a refcount leak on `$->cra_refcnt`.
```
