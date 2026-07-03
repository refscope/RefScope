# REAL BUG: drivers/gpu/drm/nouveau/dispnv04/disp.c:53 nv04_encoder_get_connector()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

- The root cause is the missing get in this function. The internal iterator reference lifecycle does **not** provide ownership to the caller.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (iterator) | PUT Done? (iterator) | Balanced? (within function) | Notes |
|------|-------------|----------------------|----------------------|----------------------------|-------|
| L52  | non-NULL nv_connector | YES (via drm_connector_list_iter_next in loop) | YES (drm_connector_list_iter_end at L50) | ✅ iterator get/put balanced | **MISSING GET for caller:** function does not take a reference on the returned connector. The “get” naming implies reference transfer, but no get is performed for the return value. |
| L52  | NULL (no match or no connectors) | YES if loop executed (gets then puts), NO if no connectors | YES (iter_end safe) | ✅ | NULL return, no ref issue. |

## Analysis

- The function uses `drm_connector_list_iter_next` (via the loop) and `drm_connector_list_iter_end`. Contracts confirm each iteration acquires a temporary reference and `iter_end` releases the final one — internally balanced.
- However, the function is named `nv04_encoder_get_connector()` — conventional kernel “get” functions must return a pointer with an additional reference held. The source contains **no explicit get** (`drm_connector_get`, `kref_get`, etc.) before returning the connector.
- Smatch’s “refcount excess put” at line 53 (function’s end) indicates that the **caller will later put a reference that was never taken**, leading to an underflow when combined with the iterator’s internal put.
- The root cause is the missing get in this function. The internal iterator reference lifecycle does **not** provide ownership to the caller.

## VERDICT: REAL_BUG
CONFIDENCE: HIGH  
Function `nv04_encoder_get_connector` fails to acquire a reference for the returned connector, violating the “get” naming convention and causing a refcount excess put when the caller releases the pointer it incorrectly assumes it owns.
```
