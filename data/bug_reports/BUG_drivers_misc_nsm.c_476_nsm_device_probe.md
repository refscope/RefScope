# REAL BUG: drivers/misc/nsm.c:476 nsm_device_probe()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L469 | return 0 (success) | YES | NO (deferred to dev removal) | ✅ | released by hwrng_unregister in remove callback |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L429 | error return -ENOMEM | NO (before any get) | N/A | ✅ | |
| L440 via err_init_vq | error return after vq init fail | NO | N/A | ✅ | no hwrng_register called yet |
| L455 via err_hwrng | error return after hwrng_register fail | YES (unconditional get, contract says always inc) | NO | ❌ LEAK | err_hwrng only calls del_vqs, missing hwrng_unregister |
| L463 via err_misc | error return after misc_register fail | YES (from hwrng_register) | YES (hwrng_unregister at L464) | ✅ | |
| L469 | return 0 (success) | YES | NO (deferred to dev removal) | ✅ | released by hwrng_unregister in remove callback |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
hwrng_register is an unconditional GET; on error path at L455 (goto err_hwrng) the matching hwrng_unregister is never called, leaking the ref.
```
