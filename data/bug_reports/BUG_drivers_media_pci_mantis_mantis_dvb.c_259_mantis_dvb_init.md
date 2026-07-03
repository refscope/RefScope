# REAL BUG: drivers/media/pci/mantis/mantis_dvb.c:259 mantis_dvb_init()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L234 | return 0    | YES (success)                     | NOT NEEDED (ref held for device lifetime)                | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? (dvb_register_frontend) | PUT Done? (dvb_unregister_frontend / dvb_frontend_detach) | Balanced? | Notes |
|------|-------------|-----------------------------------|-----------------------------------------------------------|-----------|-------|
| L151 | error       | NO (before any frontend)         | N/A                                                       | ✅ | |
| L171 | goto err0   | NO (before frontend)             | NO                                                        | ✅ | err0 only unregisters adapter |
| L183 | goto err1   | NO (before frontend)             | NO                                                        | ✅ | |
| L191 | goto err2   | NO (before frontend)             | NO                                                        | ✅ | |
| L198 | goto err3   | NO (before frontend)             | NO                                                        | ✅ | |
| L204 | goto err4   | NO (before frontend)             | NO                                                        | ✅ | |
| L214 | goto err5   | NO (before dvb_register_frontend)| NO (mantis->fe may be non‑NULL but not registered; no get) | ✅ | no get, so no put needed |
| L219 | goto err5   | NO (before dvb_register_frontend)| NO                                                        | ✅ | |
| L229 | goto err5   | **YES** (unconditional GET)      | **NO** (mantis->fe set to NULL, so the `if (mantis->fe)` block is skipped) | ❌ **LEAK** | dvb_register_frontend always increments refcount; error path fails to call dvb_frontend_detach / dvb_unregister_frontend |
| L234 | return 0    | YES (success)                     | NOT NEEDED (ref held for device lifetime)                | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
dvb_register_frontend unconditionally increments the frontend refcount; on registration failure (line 222) the code sets mantis->fe = NULL and jumps to err5, where the cleanup block is skipped, leaking the reference.
```
