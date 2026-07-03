# REAL BUG: net/sctp/outqueue.c:1084 sctp_outq_flush_data()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

timer was not already running).  The function ends with an unconditional `sctp_transport_put` at line 1084, which is reached by many paths that **never** executed the get (e.g. empty queue, abandoned chunks, closed stream, transmit failure).  This causes an excess put on the transport’s refcount.

## Full Response

```
```
| Line | Return Type            | GET Done? | PUT Done? | Balanced? | Notes |
|------|------------------------|-----------|-----------|-----------|-------|
| 1050 | early return           | NO        | N/A       | ✅        | COOKIE_ECHOED check before any transport get |
| 1060 | early return (default) | NO        | N/A       | ✅        | state disallows data, before any transport get |
| 1073 | early return           | NO        | N/A       | ✅        | retransmit flush, before transport get |
| 1084 | put + implicit return  | condition | YES       | ❌ EXCESS | `sctp_transport_put(ctx->transport)` executes even when no `sctp_transport_reset_t3_rtx` succeeded (GET=NO) |

The get `sctp_transport_reset_t3_rtx` is conditional (only holds a transport reference if the T3 timer was not already running).  The function ends with an unconditional `sctp_transport_put` at line 1084, which is reached by many paths that **never** executed the get (e.g. empty queue, abandoned chunks, closed stream, transmit failure).  This causes an excess put on the transport’s refcount.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
```
