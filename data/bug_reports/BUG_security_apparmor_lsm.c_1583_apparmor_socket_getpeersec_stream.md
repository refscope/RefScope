# REAL BUG: security/apparmor/lsm.c:1583 apparmor_socket_getpeersec_stream()

**Confidence**: HIGH | **Counter**: `$->count.count.refcount.refs.counter`

## Reasoning

| L1564 (fallthrough) | success/error (copy) | YES | YES | YES (via done_put) | YES | ❌ Excess put on peer | same |

## Full Response

```
| Line | Return Type | GET Done? (peer) | GET Done? (label) | PUT Done? (peer) | PUT Done? (label) | Balanced? | Notes |
|------|-------------|------------------|-------------------|------------------|-------------------|-----------|-------|
| L1552 (goto done) | error (peer IS_ERR) | NO (peer is ERR_PTR) | NO (label not init) | NO | NO | ✅ | No peer ref, no label ref |
| L1558 (goto done_put) | error (slen < 0) | YES (peer valid) | YES (begin_current_label_crit_section) | YES (aa_put_label at L1572) | YES (end_current_label_crit_section) | ❌ Excess put on peer | `sk_peer_get_label` does not increment refcount; `aa_put_label(peer)` is extra |
| L1562 (goto done_len) | error (slen > len) | YES | YES | YES (via done_put) | YES | ❌ Excess put on peer | same |
| L1564 (fallthrough) | success/error (copy) | YES | YES | YES (via done_put) | YES | ❌ Excess put on peer | same |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`sk_peer_get_label` returns a label pointer without a reference count increment; the function then calls `aa_put_label(peer)`, causing an excess put on the peer label’s kref.
```
