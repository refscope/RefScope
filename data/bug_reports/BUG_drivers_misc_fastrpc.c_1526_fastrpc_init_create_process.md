# REAL BUG: drivers/misc/fastrpc.c:1526 fastrpc_init_create_process()

**Confidence**: HIGH | **Counter**: `map->refcount.refcount.refs.counter`

## Reasoning

| ~L1493| success     | YES (map_create succeeded) | NO  | ❌ **LEAK** | map reference never released before return |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1420 | error       | NO (before any get) | N/A  | ✅ | early ENOMEM before alloc |
| L1426 | goto err    | NO (before map_create) | N/A  | ✅ | copy_from_user failure |
| ~L1433| goto err    | NO (before map_create) | N/A  | ✅ | session rejected |
| L1438 | goto err    | NO (before map_create) | N/A  | ✅ | filelen too large |
| L1451 | goto err    | NO (conditional GET failed) | N/A  | ✅ | map_create returned error, map NULL |
| L1457 | goto err_alloc| YES (map_create succeeded) | YES (via err_alloc→fastrpc_map_put) | ✅ | early buf_alloc failure releases map |
| L1491 | goto err_invoke| YES (map_create succeeded) | YES (falls through to err_alloc→put) | ✅ | invoke failure releases map |
| ~L1493| success     | YES (map_create succeeded) | NO  | ❌ **LEAK** | map reference never released before return |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On success path after fastrpc_map_create, the obtained map reference is not released because the function returns 0 without fastrpc_map_put(map), leaking the refcount.
```
