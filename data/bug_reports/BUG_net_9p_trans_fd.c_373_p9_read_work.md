# REAL BUG: net/9p/trans_fd.c:373 p9_read_work()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L347-L350 (status else) | goto error | YES | NO | ❌ LEAK | no put before error |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L250 | early return (error check) | NO (before get) | N/A | ✅ | m->err < 0, no rreq |
| L268 | goto end_clear (EAGAIN) | NO | N/A | ✅ | err == -EAGAIN, no rreq set |
| L270 | goto error (fatal read) | NO | N/A | ✅ | err ≤ 0, no rreq |
| L280 | goto error (parse error) | NO | N/A | ✅ | before p9_tag_lookup |
| L287-L290 (m->rreq NULL) | goto error | NO (lookup failed) | N/A | ✅ | rreq is NULL, no ref held |
| L287-L290 (m->rreq valid, status != SENT) | goto error | YES | NO | ❌ LEAK | get via p9_tag_lookup, no put on error |
| L295-L300 (size too big) | goto error | YES | NO | ❌ LEAK | m->rreq valid, goto error skips put |
| L302-L309 (no sdata) | goto error | YES | YES | ✅ | explicit put then m->rreq=NULL before error |
| L312-L330 (skip packet block) | goto end_clear | YES | NO | ✅ (deferred) | long-term hold, put on future packet completion |
| L332-L346 (status == SENT) | fall through to end_clear after block | YES | YES+DUP ❌ | ❌ EXCESS PUT | p9_client_cb drops ref then p9_req_put drops again, two puts for one get |
| L332-L346 (status == FLUSHED) | fall through | YES | YES | ✅ | no cb, one put |
| L347-L350 (status else) | goto error | YES | NO | ❌ LEAK | no put before error |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the success path for REQ_STATUS_SENT, `p9_client_cb` (which does an unconditional `p9_req_put`) is called followed by another `p9_req_put` at L373, resulting in a double put and excess refcount drop.
```
