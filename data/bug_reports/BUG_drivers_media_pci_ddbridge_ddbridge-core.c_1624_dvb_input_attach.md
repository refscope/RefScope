# REAL BUG: drivers/media/pci/ddbridge/ddbridge-core.c:1624 dvb_input_attach()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| default case in switch | return 0 | NO | N/A | ✅ | |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~1460| return ret (dvb_dmx_init err) | NO (before any dvb_register_frontend) | N/A | ✅ | |
| ~1475| goto err_detach (dvb_dmxdev_init err) | NO | N/A | ✅ | |
| ~1485| goto err_detach (connect_frontend err) | NO | N/A | ✅ | |
| ~1490| goto err_detach (dvb_net_init err) | NO | N/A | ✅ | |
| multiple switch cases: demod_attach err → goto err_detach | NO (no register yet) | N/A | ✅ | Frontends allocated but not registered; err_detach→dvb_input_detach possibly handles. |
| multiple switch cases: tuner_attach err → goto err_tuner | NO (no register yet) | N/A | ✅ | Detach cleans allocated but unregistered frontends. |
| ~1578 | goto err_detach after dvb_register_frontend(fe) < 0 | **YES** (fe get) | **NO** (no unregister for fe) | ❌ LEAK | Unconditional get; fe must be unregistered/put on error. |
| ~1586 | goto err_detach after dvb_register_frontend(fe2) < 0 (unregisters fe) | **YES** (fe2 get) | **NO** (no unregister for fe2) | ❌ LEAK | Only fe is unregistered; fe2 leaked. |
| ~1590 | return 0 (success) | YES (both gets) | YES (kept for framework) | ✅ | Framework owns references, released on dvb_unregister_frontend later. |
| default case in switch | return 0 | NO | N/A | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unconditional get from dvb_register_frontend leaks on two error paths: goto err_detach after fe registration fails (missing put for fe) and after fe2 registration fails (missing put for fe2).```
```
