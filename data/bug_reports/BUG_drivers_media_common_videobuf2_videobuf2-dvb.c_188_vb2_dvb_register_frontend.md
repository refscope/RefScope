# REAL BUG: drivers/media/common/videobuf2/videobuf2-dvb.c:188 vb2_dvb_register_frontend()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L165 (goto fail_fe_conn) | error (connect_frontend fails) | YES | YES + YES | ❌ EXCESS PUT | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L175 (return 0) | success | YES (dvb_register_frontend succeeded) | NO | ✅ (subsystem holds ref) | OK, reference held by adapter |
| L110 (goto fail_frontend) | error (register fails) | Contract says unconditional → YES | YES (dvb_frontend_detach at L188) | ✅ (if contract correct) | Only one put, balanced |
| L128 (goto fail_dmx) | error (dmx init fails) | YES (register succeeded) | YES (dvb_unregister_frontend at L185) + YES (dvb_frontend_detach at L188) | ❌ EXCESS PUT | **Double put** |
| L135 (goto fail_dmxdev) | error (dmxdev init fails) | YES | YES (cascade → dvb_unregister_frontend) + YES (dvb_frontend_detach) | ❌ EXCESS PUT | |
| L145 (goto fail_fe_hw) | error (add_frontend fe_hw fails) | YES | YES + YES | ❌ EXCESS PUT | |
| L155 (goto fail_fe_mem) | error (add_frontend fe_mem fails) | YES | YES + YES | ❌ EXCESS PUT | |
| L165 (goto fail_fe_conn) | error (connect_frontend fails) | YES | YES + YES | ❌ EXCESS PUT | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After dvb_register_frontend() succeeds, all subsequent error paths call both dvb_unregister_frontend() (put) and dvb_frontend_detach() (put), causing an excess put (refcount underflow) at line 188.
```
