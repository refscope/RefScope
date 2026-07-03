# REAL BUG: net/netfilter/nft_set_hash.c:495 nft_rhash_gc()

**Confidence**: MEDIUM | **Counter**: `$->set->refs.refs.counter`

## Reasoning

ES at ~L477 via queue_async_done? but if catchall already enqueued, double put | ⚠️     | if catchall_async enqueues old gc and returns the same pointer, queue_async_done re‑enqueues and puts again → excess put |

## Full Response

```
| Line | Return Type    | GET Done? | PUT Done? | Balanced? | Notes |
|------|----------------|-----------|-----------|-----------|-------|
| ~L418 | goto done (pending) | NO        | NO        | ✅        | set->gc pending, no refs taken |
| ~L421 | goto done (alloc fail) | NO        | NO        | ✅        | gc null, no refs |
| ~L432 | error (IS_ERR) → try_later | YES (from prior queue_async if any, but current gc's ref destroyed) | YES (destroy) | ✅ | destroy releases outstanding gc ref |
| ~L439 | error (gc_seq change) → try_later | YES (same logic) | YES (destroy) | ✅ | |
| ~L460 | dead_elem, queue_async fails (gc=NULL) → try_later | NO (new gc not obtained) | NO        | ✅ | old gc enqueued, no outstanding ref |
| ~L460 | dead_elem, queue_async succeeds → loop continues | YES (new gc ref obtained) | NO (yet)  | ⏳      | accumulates refs; final put later |
| ~L471 | catchall_async → try_later (gc non‑null) | dependency on catchall_async (if it returns with ref) | YES at ~L477 via queue_async_done? but if catchall already enqueued, double put | ⚠️     | if catchall_async enqueues old gc and returns the same pointer, queue_async_done re‑enqueues and puts again → excess put |
| ~L471 | catchall_async → try_later (gc NULL) | NO        | NO        | ✅        | |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
nft_rhash_gc() calls nft_trans_gc_catchall_async() at ~L471; if that function enqueues the gc (transferring its set reference) but returns a non‑NULL pointer (the same drained gc), the subsequent nft_trans_gc_queue_async_done(gc) at ~L477 will attempt another put on the set, resulting in the excess put detected at line 495. Without the callee source this cannot be fully confirmed, but the pattern matches a known double‑put risk.
```
