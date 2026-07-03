# REAL BUG: net/sctp/socket.c:1890 sctp_sendmsg_to_asoc()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| ~1885 (success, return msg_len) | success | YES (holds transferred to lower send layer) | YES (send consumes holds; sctp_datamsg_put for datamsg) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~1796 (goto err: sinfo->sinfo_stream >= asoc->stream.outcnt) | error | NO (before GET) | N/A | ✅ | |
| ~1804 (goto err: sctp_stream_init_ext failure) | error | NO | N/A | ✅ | |
| ~1809 (goto err: disable_fragments) | error | NO | N/A | ✅ | |
| ~1824 (goto err: sctp_wait_for_sndbuf failure) | error | NO | N/A | ✅ | |
| ~1831 (goto err: sctp_primitive_ASSOCIATE failure) | error | NO | N/A | ✅ | |
| ~1842 (goto err: sctp_wait_for_connect failure) | error | NO | N/A | ✅ | |
| ~1855 (IS_ERR(datamsg) goto err) | error | NO (conditional get failed) | N/A | ✅ | sctp_datamsg_from_user returned error, no get |
| ~1868 (sctp_primitive_SEND failure, goto err after sctp_datamsg_free) | error | YES (sctp_chunk_hold for every chunk – unconditional) | NO (sctp_datamsg_free releases one reference per chunk, but holds remain) | ❌ LEAK | Chunk refcounts leaked; holds not consumed because send failed |
| ~1885 (success, return msg_len) | success | YES (holds transferred to lower send layer) | YES (send consumes holds; sctp_datamsg_put for datamsg) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the sctp_primitive_SEND failure path, chunks receive an unconditional get via sctp_chunk_hold(), but sctp_datamsg_free() only releases the original datamsg‑own references, leaving the extra holds unreleased and causing a per‑chunk refcount leak.
```
