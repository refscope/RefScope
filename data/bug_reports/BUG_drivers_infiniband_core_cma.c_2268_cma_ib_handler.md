# REAL BUG: drivers/infiniband/core/cma.c:2268 cma_ib_handler()

**Confidence**: HIGH | **Counter**: `$->id.context->re_kref.refcount.refs.counter`

## Reasoning

(destroy -> cma_id_put -> cma_release_id -> rdma_restrack_put) + **potentially extra PUT inside cma_cm_event_handler on error** | ❌ EXCESS PUT if handler already did a put | smatch sees a put on re_kref via destroy, and an earlier get from handler; if handler also does put on error → double put |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| early condition goto out -> return 0 | no-op/error | NO (before any get) | NO | ✅ | handler not called, no ref |
| DREQ_ERROR goto out -> return 0 | no-op/error | NO (before handler) | NO | ✅ | early out, no ref |
| MRA_RECEIVED goto out -> return 0 | ignore / no-op | NO | NO | ✅ | handler skipped |
| default goto out -> return 0 | error / no-op | NO | NO | ✅ | handler skipped |
| handler returns 0, goto out, return 0 | success | YES (get in handler) | NO (put deferred to user handler or later) | ⚠️ leak if not transferred, but not excess put | ownership pattern; not this warning |
| handler returns !=0, destroy_id_handler_unlock, return ret | error | YES (get in handler) | YES (destroy -> cma_id_put -> cma_release_id -> rdma_restrack_put) + **potentially extra PUT inside cma_cm_event_handler on error** | ❌ EXCESS PUT if handler already did a put | smatch sees a put on re_kref via destroy, and an earlier get from handler; if handler also does put on error → double put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
cma_cm_event_handler() calls destroy_id_handler_unlock() on error before returning, and cma_ib_handler() then calls it again, leading to a double kref_put on re_kref.refcount.
```
```
