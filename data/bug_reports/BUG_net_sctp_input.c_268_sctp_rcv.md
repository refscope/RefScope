# REAL BUG: net/sctp/input.c:268 sctp_rcv()

**Confidence**: MEDIUM | **Counter**: `chunk->refcnt.refs.counter`

## Reasoning

| 115-118 / 126 | success (sctp_inq_push) | YES (chunk created) | NO (ownership → inqueue) | ❌ EXCESS PUT | sctp_inq_push contract says unconditional → sctp_chunk_free(put), sctp_chunk_free(put); double‑put in callee causes chunk refcount to go negative |

## Full Response

```
| Line | Return Type | GET Done? (sctp_chunkify) | PUT Done? (sctp_chunk_free) | Balanced? | Notes |
|------|-------------|---------------------------|-----------------------------|-----------|-------|
| 18   | error (discard_it) | NO (before chunkify) | N/A | ✅ | packet type check |
| 25   | error (discard_it) | NO (before chunkify) | N/A | ✅ | too small |
| 30   | error (discard_it) | NO (before chunkify) | N/A | ✅ | linearize/pull fail |
| 41   | error (discard_it) | NO (before chunkify) | N/A | ✅ | checksum fail |
| 49   | error (discard_it) | NO (before chunkify) | N/A | ✅ | unknown address family |
| 59   | error (discard_it) | NO (before chunkify) | N/A | ✅ | non‑unicast address |
| 75   | error (discard_release) | NO (before chunkify) | N/A | ✅ | OOTB packet |
| 80   | error (discard_release) | NO (before chunkify) | N/A | ✅ | xfrm policy check |
| 84   | error (discard_release) | NO (before chunkify) | N/A | ✅ | sk_filter / short chunk |
| 89   | error (chunk==NULL) | NO (get failed) | N/A | ✅ | chunk allocation failure |
| 110  | error (backlog fail) | YES (chunk created) | YES (line 108 sctp_chunk_free) | ✅ | explicit free, then goto discard_release |
| 112-118 / 126 | success (backlog success) | YES (chunk created) | NO (ownership → backlog) | ✅ | freed later by backlog processing; no immediate put needed |
| 115-118 / 126 | success (sctp_inq_push) | YES (chunk created) | NO (ownership → inqueue) | ❌ EXCESS PUT | sctp_inq_push contract says unconditional → sctp_chunk_free(put), sctp_chunk_free(put); double‑put in callee causes chunk refcount to go negative |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
sctp_inq_push() contract indicates unconditional double-put on the chunk, leading to an excess put of chunk->refcnt; the calling code in sctp_rcv() correctly transfers ownership, so the bug is in sctp_inq_push but the warning correctly identifies a refcount violation triggered through this path.
```
