# REAL BUG: net/sctp/sm_statefuns.c:4194 sctp_sf_do_reconf()

**Confidence**: HIGH | **Counter**: `$->strreset_chunk->refcnt.refs.counter`

## Reasoning

` unconditional put) | ❌ **EXCESS PUT** | The function unconditionally calls `sctp_process_strreset_resp` when `param.p->type == SCTP_PARAM_RESET_RESPONSE`. No preceding `sctp_process_strreset_inreq` (unconditional GET) is required, causing a put without a matching get on `asoc->strreset_chunk`. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4140 (vtag verify fail) | `sctp_sf_pdiscard` | NO | NO | ✅ | No get/put in this path |
| L4147 (chunk length invalid) | `sctp_sf_violation_chunklen` | NO | NO | ✅ | |
| L4152 (verify reconf fail) | `sctp_sf_violation_paramlen` | NO | NO | ✅ | |
| L4198 (success, no RESPONSE param or RESP without prior GET) | `SCTP_DISPOSITION_CONSUME` | NO (no unconditional GET for `strreset_chunk` in this function) | YES (via `sctp_process_strreset_resp` unconditional put) | ❌ **EXCESS PUT** | The function unconditionally calls `sctp_process_strreset_resp` when `param.p->type == SCTP_PARAM_RESET_RESPONSE`. No preceding `sctp_process_strreset_inreq` (unconditional GET) is required, causing a put without a matching get on `asoc->strreset_chunk`. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`sctp_sf_do_reconf()` calls `sctp_process_strreset_resp` (unconditional PUT on `asoc->strreset_chunk`) without any prior unconditional GET on that chunk. An incoming RESET_RESPONSE parameter without a preceding RESET_IN_REQUEST leads to an excess put, potentially causing refcount underflow and use-after-free.
```
