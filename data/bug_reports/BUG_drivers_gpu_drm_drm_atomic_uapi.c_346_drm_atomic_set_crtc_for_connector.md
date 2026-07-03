# REAL BUG: drivers/gpu/drm/drm_atomic_uapi.c:346 drm_atomic_set_crtc_for_connector()

**Confidence**: HIGH | **Counter**: `$->base.refcount.refcount.refs.counter`

## Reasoning

| ~370 | IS_ERR return (old crtc == NULL, crtc non‑NULL, drm_atomic_get_crtc_state fails) | NO (failure before get) | NO (no old block) | ✅ | No put performed, no ref held |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~312 | early return (conn_state->crtc == crtc) | NO | NO | ✅ | No state change, no ref operations |
| ~370 | IS_ERR return (old crtc non‑NULL, crtc non‑NULL, drm_atomic_get_crtc_state fails) | NO (failure before get) | YES (L346) | ❌ LEAK / EXCESS PUT | PUT executed but no matching GET; old reference dropped prematurely |
| ~385 | final return 0 (old crtc non‑NULL, crtc == NULL) | NO | YES (L346) | ✅ | Intentional detach, net decrease correct |
| ~385 | final return 0 (old crtc non‑NULL, crtc non‑NULL, get succeeded) | YES | YES (L346) | ✅ | Balanced: old reference replaced by new |
| ~385 | final return 0 (old crtc == NULL, crtc non‑NULL, get succeeded) | YES | NO | ✅ | Only new reference added |
| ~370 | IS_ERR return (old crtc == NULL, crtc non‑NULL, drm_atomic_get_crtc_state fails) | NO (failure before get) | NO (no old block) | ✅ | No put performed, no ref held |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`drm_connector_put` at L346 is executed unconditionally when `conn_state->crtc` is non‑NULL, releasing the old CRTC reference. If the subsequent `drm_atomic_get_crtc_state` fails, the function returns an error without calling `drm_connector_get`. This premature put leaves the connector with an unbalanced reference count (excess put), potentially causing an underflow and use‑after‑free. The order of operations should not drop the old reference until the new reference is safely acquired.
```
