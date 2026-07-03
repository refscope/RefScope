# REAL BUG: drivers/media/pci/bt8xx/dvb-bt8xx.c:711 frontend_init()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L~611/L~631/L~660/L~679 (goto error_out from 0x1016/0x1018/0x101c/0x1020 cases) | goto error_out→detach→return | YES (initial ref from dvb_attach) | YES (single) | ✅ | Correct release of the frontend before registration |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L~700 (budget->dvb_frontend==NULL, return) | return (void) | NO (no frontend obtained) | NO | ✅ | No ref held, no detach needed |
| L~707 (successful dvb_register_frontend, return) | return (void) | YES (initial ref from dvb_attach + registration ref) | NO (held for adapter lifetime) | ✅ | Reference handed to adapter, future detach handles it |
| L~707→goto error_out (dvb_register_frontend fails) | goto error_out→detach→return | YES (initial ref from dvb_attach) | YES (but double put) | ❌ EXCESS PUT | dvb_register_frontend already released its internal ref on error, → dvb_frontend_detach causes underflow |
| L~611/L~631/L~660/L~679 (goto error_out from 0x1016/0x1018/0x101c/0x1020 cases) | goto error_out→detach→return | YES (initial ref from dvb_attach) | YES (single) | ✅ | Correct release of the frontend before registration |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

When `dvb_register_frontend()` fails, it internally does a `dvb_frontend_put` (as per contract), releasing its own reference. The `goto error_out` then calls `dvb_frontend_detach()` again, leading to a double put and refcount underflow. The bug is on the error path at line 711.
```
