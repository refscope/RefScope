# REAL BUG: net/sctp/stream.c:421 sctp_send_reset_assoc()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L421 (success) | return 0 | YES (hold ref + alloc ref) | NO (intentional deferred) | ✅ (targeted for later cleanup) | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L389 | error (-ENOPROTOOPT) | NO (before get) | N/A  | ✅ | |
| L392 | error (-EINPROGRESS) | NO (before get) | N/A  | ✅ | |
| L395 | error (-EAGAIN) | NO (before get) | N/A  | ✅ | |
| L399 | error (-ENOMEM) | NO (chunk alloc failed) | N/A  | ✅ | |
| L416 (error path) | error return retval | YES (sctp_chunk_hold at L406) | YES (sctp_chunk_put at L410) | ❌ EXCESS PUT | sctp_send_reconf() contract shows conditional sctp_chunk_free (put) on some paths, possibly twice. If send_reconf already put the chunk on error, the caller’s extra sctp_chunk_put becomes an excess put, potentially on an already freed chunk. |
| L421 (success) | return 0 | YES (hold ref + alloc ref) | NO (intentional deferred) | ✅ (targeted for later cleanup) | |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
sctp_send_reconf() may free the chunk on error (contract shows sctp_chunk_free calls), and the error path unconditionally calls sctp_chunk_put(asoc->strreset_chunk), leading to an excess put and possible use-after-free. The caller must not put the chunk if sctp_send_reconf already consumed it.
```
