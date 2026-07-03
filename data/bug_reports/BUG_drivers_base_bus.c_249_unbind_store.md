# REAL BUG: drivers/base/bus.c:249 unbind_store()

**Confidence**: HIGH | **Counter**: `bus->p.subsys.kobj.kref.refcount.refs.counter`

## Reasoning

All return paths leave the bus reference undropped. Leak is present on both the early-exit and normal-exit paths.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L24 | early error return (`dev==NULL`) | YES (if bus valid, `bus_find_device_by_name` calls `bus_get()` internally) | NO | ❌ LEAK | Bus ref taken, not released |
| L33 | normal return | YES (same as above) | NO | ❌ LEAK | Bus ref taken, `bus_put()` never called |

- **GET**: `bus_get()` is called within `bus_find_device_by_name` (conditional – succeeds if bus refcount >0, returning non-NULL bus pointer) and a reference is held on the `bus->p.subsys.kobj.kref` counter.  
- **PUT**: No `bus_put()` appears anywhere in `unbind_store` or in `bus_find_device_by_name` (old kernel version). The `put_device(dev)` only releases the device reference from `get_device()` inside `bus_find_device_by_name`, not the bus reference.

All return paths leave the bus reference undropped. Leak is present on both the early-exit and normal-exit paths.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`bus_find_device_by_name` takes a bus reference via `bus_get()` and neither the callee nor `unbind_store` releases it with `bus_put()`, leaking the bus kref on all return paths.
```
