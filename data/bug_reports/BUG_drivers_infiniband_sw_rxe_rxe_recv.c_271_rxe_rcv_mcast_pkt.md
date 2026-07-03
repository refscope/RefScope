# REAL BUG: drivers/infiniband/sw/rxe/rxe_recv.c:271 rxe_rcv_mcast_pkt()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

- Path 4 is not a leak in this function; the earlier `ib_device_try_get` successes are handed off; they must be released elsewhere. Balanced from this function’s perspective.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| mcg NULL → goto drop (L210→L271) | implicit end | NO (no get called) | YES (ib_device_put) | ❌ EXCESS PUT | No ib_device_try_get, yet put is called |
| loop break after ib_device_try_get fails (WARN_ON) → after loop skb non-NULL → fall through to drop (L271) | implicit end | NO (get failed) | YES (ib_device_put) | ❌ EXCESS PUT | get attempt failed, no ref held |
| loop ends, skb non-NULL (last QP checks fail or list empty) → fall through to drop (L271) | implicit end | NO (no get in this path)¹ | YES (ib_device_put) | ❌ EXCESS PUT | ¹ if no non-last QP had a successful get (otherwise leak but not excess) – a path with zero gets exists |
| loop ends, skb is NULL (last QP consumed skb) → early return (L268) | explicit return | YES (possible gets for non-last QPs) | NO | ⚠️ ² | no put in this function; gets passed to rxe_rcv_pkt |

Footnotes:
- Path 3 represents any scenario where the loop terminates without consuming the skb and without calling ib_device_try_get (e.g., checking fails on the last QP, or the list is empty). Even if some non-last QPs successfully got the device, there exists a pure path with no get at all → excess put.
- Path 4 is not a leak in this function; the earlier `ib_device_try_get` successes are handed off; they must be released elsewhere. Balanced from this function’s perspective.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ib_device_put` at drop label executed on paths where `ib_device_try_get` was never called or failed, causing excess put.
```
