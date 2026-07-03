# REAL BUG: crypto/algapi.c:474 crypto_register_alg()

**Confidence**: HIGH | **Counter**: `$->cra_refcnt.refs.counter`

## Reasoning

| ~467 (IS_ERR(larval)) | error (PTR_ERR) | YES | YES (crypto_alg_put(alg)) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~437 (err) | error | NO (crypto_check_alg returned err, refcount not set) | N/A | ✅ | |
| ~445 (kmemdup failure) | error (-ENOMEM) | YES (crypto_check_alg succeeded, cra_refcnt set to initial value) | NO | ❌ LEAK | original alg lost, no put, reference held by alg not released |
| ~467 (IS_ERR(larval)) | error (PTR_ERR) | YES | YES (crypto_alg_put(alg)) | ✅ | |
| ~470 (success) | success (0) | YES | NO (ownership transferred to crypto subsystem) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error path after kmemdup failure leaks reference: crypto_check_alg succeeded but original alg’s ref is never put.
```
