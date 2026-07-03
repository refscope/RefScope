# REAL BUG: drivers/gpu/drm/nouveau/nouveau_connector.c:1496 nouveau_connector_create()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

| L1491 | return connector (success) | drm_connector_init set ref=1 → GET | N/A | ✅ | Returns newly created connector with reference for caller. |

## Full Response

```
| Line | Return Type | GET Done? (caller's ref) | PUT Done? (function's reference) | Balanced? | Notes |
|------|-------------|--------------------------|----------------------------------|-----------|-------|
| L1299 | return connector (success) | **NO** (iterator's get was dropped by iter_end) | iter_end PUT (drops iterator ref) | ❌ MISSING GET | Returns existing connector without acquiring a reference for the caller. Caller later does `drm_connector_put` → **excess put**. Bug: need `drm_connector_get()` before iter_end. |
| L1306 | return ERR_PTR(-ENOMEM) | N/A | N/A | ✅ | No connector allocated |
| L1317 | return ERR_PTR(ret) | N/A | N/A | ✅ | `nvif_conn_ctor` failed, kfree, no connector ref |
| L1331 | return NULL | N/A | N/A | ✅ (ref-wise, but leaky memory) | Switch default returns bare NULL; no `drm_connector_init`, no ref |
| L1397 | return ERR_PTR(ret) | drm_connector_init set ref=1 → GET | NO PUT | ❌ REF LEAK | Error path after init; kfree without put leaks reference. (Not the excess put warning) |
| L1444 → L1496 | return ERR_PTR(ret) | drm_connector_init set ref=1 → GET | NO PUT | ❌ REF LEAK | Error path goto drm_conn_err; cleanup+kfree without put, leaks reference. |
| L1491 | return connector (success) | drm_connector_init set ref=1 → GET | N/A | ✅ | Returns newly created connector with reference for caller. |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
Early return at L1299 drops the iterator’s reference via `drm_connector_list_iter_end` without acquiring a reference for the caller. The caller later calls `drm_connector_put` on the returned connector, triggering an **excess put** because the reference wasn’t taken. Fix: add `drm_connector_get(connector)` before `drm_connector_list_iter_end`.
```
