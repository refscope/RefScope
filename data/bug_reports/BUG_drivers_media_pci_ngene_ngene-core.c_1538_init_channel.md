# REAL BUG: drivers/media/pci/ngene/ngene-core.c:1538 init_channel()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1526 | return ret (success) | YES | NO (held for device lifetime) | ✅ | not a leak |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1455 | goto err (demod_attach fail) | NO (chan->fe NULL) | NO (if guard) | ✅ | no frontend, safe |
| L1460 | goto err (tuner_attach fail) | NO (dvb_register_frontend not called) | YES (dvb_frontend_detach) | ❌ EXCESS PUT | frontend’s kref not acquired → underflow |
| L1464 | return 0 (early) | NO (fe may be non-NULL but no register) | NO | ⚠️ leak, not excess put | unrelated to warning |
| L1479 | goto err (adapter reg fail) | NO | YES | ❌ EXCESS PUT | same: no dvb_register_frontend call |
| L1489 | goto err (ci init fail) | NO | YES | ❌ EXCESS PUT | no register yet |
| L1495 | goto err (ci device fail) | NO | YES | ❌ EXCESS PUT | no register yet |
| L1499 | goto err (fe reg fail) | YES (unconditional GET, contract) | YES | ✅ | register did get then put in err |
| L1504 | goto err (fe2 reg fail) | YES (fe already registered) | YES | ✅ | balances fe’s reference |
| L1526 | return ret (success) | YES | NO (held for device lifetime) | ✅ | not a leak |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`dvb_frontend_detach` is called on `chan->fe` in the error label when `dvb_register_frontend` has never been executed (L1460, L1479, L1489, L1495). The contract shows `dvb_register_frontend` is the unconditional GET that initialises and acquires the kref; without it the frontend’s refcount is uninitialised/zero, and the put causes an underflow (excess put), matching the warning.
```
