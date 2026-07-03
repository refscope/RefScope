# REAL BUG: drivers/gpu/drm/sun4i/sun4i_tcon.c:56 sun4i_tcon_get_connector()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

| L55  | NULL        | NO (last `iter_next` returned NULL, no ref taken) | YES (via `iter_end`, but no ref to release) | ✅ | Normal end-of-list cleanup, safe |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L52  | connector (non-NULL) | YES (via `drm_connector_list_iter_next`) | YES (via `drm_connector_list_iter_end`) | ❌ EXTRA PUT | `iter_end` releases iterator’s reference, leaving returned pointer without a valid refcount; caller will later `put` → excess put (double release) and possible use-after-free |
| L55  | NULL        | NO (last `iter_next` returned NULL, no ref taken) | YES (via `iter_end`, but no ref to release) | ✅ | Normal end-of-list cleanup, safe |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Calling `drm_connector_list_iter_end` before returning the connector drops the only reference, causing a double-put when the caller eventually releases it. The fix is to call `drm_connector_get(connector)` before `drm_connector_list_iter_end` to preserve a valid reference.
```
