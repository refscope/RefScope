# REAL BUG: drivers/media/pci/ttpci/budget-av.c:1347 frontend_init()

**Confidence**: LOW | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

ut. Until the exact behaviour of `dvb_register_frontend` is confirmed, the path with registration failure followed by `error_out` is suspect. All other `goto error_out` paths are safe (only the attach reference exists). Therefore the bug is concentrated on the `dvb_register_frontend` failure path.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L487‑… (switch, attach success, break, register success, `return`) | success | YES (attach ref) | NO (held for device lifetime) | ✅ (delayed put after unregister) | ref released via `dvb_frontend_detach` on unregister |
| L… (`goto error_out` after `dvb_register_frontend` failure) | error | YES (attach ref) | YES (`dvb_frontend_detach`) | ❌ **POTENTIAL EXCESS** | `dvb_register_frontend` may already `dvb_frontend_put` the attach ref on error → this detach would be a 2nd put, triggering “refcount excess put” |
| L… (`goto error_out` from case 0x1016 lnbp21 fail) | error | YES | YES | ✅ | attach ref only; detach is correct |
| L… (`goto error_out` from case 0x1018 lnbp21 fail) | error | YES | YES | ✅ | same |
| L… (`goto error_out` from case 0x101c stv6110x/isl6423 fail) | error | YES | YES | ✅ | same |
| L… (`goto error_out` from case 0x1020 stv6110x/lnbh24 fail) | error | YES | YES | ✅ | same |
| L… (budget->dvb_frontend==NULL after switch, `return`) | error | NO | N/A | ✅ | no frontend attached |

[NEED_SOURCE] dvb_register_frontend

**Analysis**:  
The runtime warning `refcount excess put` at the `dvb_frontend_detach` call (line 1347) indicates the kref was zero before the put. This can only happen if a prior put already freed the refcount, and the most plausible prior put is inside `dvb_register_frontend` on failure. The contract for `dvb_register_frontend` lists `dvb_frontend_put` as an unconditional operation – it may release the attach reference on error, making the subsequent `dvb_frontend_detach` a double-put. Until the exact behaviour of `dvb_register_frontend` is confirmed, the path with registration failure followed by `error_out` is suspect. All other `goto error_out` paths are safe (only the attach reference exists). Therefore the bug is concentrated on the `dvb_register_frontend` failure path.

VERDICT: REAL_BUG  
CONFIDENCE: LOW
```
