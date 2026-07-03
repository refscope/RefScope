# REAL BUG: net/sctp/stream.c:377 sctp_send_reset_streams()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| Success path (retval == 0) | success (0) | YES | NO (held in asoc->strreset_chunk) | ✅ (long-term ref) | chunk kept for later release |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L272 (goto out) | error (-ENOPROTOOPT) | NO (before get) | N/A | ✅ | |
| L278 (goto out) | error (-EINPROGRESS) | NO (before get) | N/A | ✅ | |
| L287 (goto out) | error (no out/in) | NO (before get) | N/A | ✅ | |
| Various goto out in str_nums checks | error (-EINVAL) | NO (before get) | N/A | ✅ | e.g. L296, L302, L310 |
| L319 (goto out after kcalloc fail) | error (-ENOMEM) | NO (before get) | N/A | ✅ | |
| L329 (goto out after outq check) | error (-EAGAIN) | NO (before get) | N/A | ✅ | |
| L335 (goto out if !chunk) | error (-ENOMEM) | NO (chunk NULL) | N/A | ✅ | |
| L377 (if retval) → goto out | error (non-zero retval) | YES (sctp_chunk_hold at L376) | YES (sctp_chunk_put inside if) | ❌ EXCESS PUT | sctp_send_reconf() already frees/puts chunk on error (contract: conditional_on_path→sctp_chunk_free), leading to double-free |
| Success path (retval == 0) | success (0) | YES | NO (held in asoc->strreset_chunk) | ✅ (long-term ref) | chunk kept for later release |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The call `sctp_chunk_put(asoc->strreset_chunk)` on the error path (line ~377) is an excess put because `sctp_send_reconf()` already consumes/releases the chunk internally on failure (contract shows conditional `sctp_chunk_free(put)`), causing a double-free.
```
