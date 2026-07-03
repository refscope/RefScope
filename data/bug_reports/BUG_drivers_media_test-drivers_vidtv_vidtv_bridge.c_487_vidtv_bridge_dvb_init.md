# REAL BUG: drivers/media/test-drivers/vidtv/vidtv_bridge.c:487 vidtv_bridge_dvb_init()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| ~L461 (fail_dmx_conn) | error → unregister all → return | YES | YES | ✅ | |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L421 (fail_i2c) | error → return | NO (before any FE ops) | N/A | ✅ | no frontend registered |
| ~L424 (fail_adapter) | error → return | NO | N/A | ✅ | no frontend registered |
| ~L431 (fail_demod_probe, probe_demod fails) | error → cleanup → return | YES for previous registered FEs, NO for current i | YES via `dvb_unregister_frontend` loop | ✅ | current i FE not yet registered |
| ~L436 (fail_tuner_probe) | error → cleanup → return | NO for current i (FE not registered) | YES for previous registered FEs | ✅ | |
| **~L443 (fail_fe, dvb_register_frontend fails)** | error → cleanup → return | **YES** (unconditional get from `dvb_register_frontend`) | **NO** (`dvb_unregister_frontend` not called for current `i`) | **❌ LEAK** | reference taken but never released |
| ~L448 (fail_dmx) | error → unregister all → return | YES (all FEs registered) | YES (unregister loop) | ✅ | |
| ~L453 (fail_dmx_dev) | error → unregister all → return | YES | YES | ✅ | |
| ~L461 (fail_dmx_conn) | error → unregister all → return | YES | YES | ✅ | |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

`dvb_register_frontend` unconditionally takes a reference on the frontend’s kref (per contract). On failure (`goto fail_fe`), the cleanup only releases the tuner and demod for the current index but does **not** call `dvb_unregister_frontend` or `dvb_frontend_put`, leaking the reference.
```
