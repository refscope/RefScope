# REAL BUG: drivers/infiniband/hw/irdma/cm.c:2893 irdma_handle_ack_pkt()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L2897 | success (default: SYN_SENT, FIN_WAIT2, OFFLOADED, MPAREQ_RCVD, UNKNOWN) | NO (none) | YES (irdma_cleanup_retrans_entry at L2893) | ❌ EXCESS PUT | no retrans entry exists in these states → refcount underflow |

## Full Response

```
[NEED_SOURCE] irdma_cleanup_retrans_entry

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2834 | error       | NO  | NO   | ✅ | early seq check, no ref ops |
| L2842 | error (SYN_RCVD) | NO (none in func) | YES (irdma_cleanup_retrans_entry) | ✅ (external get) | retrans ref held from prior state transition |
| L2849 | success (SYN_RCVD, tcp_options ok) | NO (none in func) | YES (cleanup) | ✅ (external get) | same as above |
| L2856 | success (ESTABLISHED) | NO (none) | YES (cleanup) | ✅ (external get) | retrans ref held |
| L2866 | success (MPAREQ_SENT) | NO (none) | NO (no cleanup) | ✅ | no get/put |
| L2871 | success (LISTENING) | NO (none) | YES (cleanup) | ✅ (external get) | retrans ref held |
| L2876 | success (CLOSED) | YES (refcount_inc) | NO (no put) | ❌ LEAK | get without put – leak (not the reported bug) |
| L2882 | success (LAST_ACK / CLOSING) | NO (none) | YES (cleanup + rem_ref) | ❌ EXCESS PUT (or double put) | two puts, no get; likely bug |
| L2886 | success (FIN_WAIT1) | NO (none) | YES (cleanup) | ✅ (external get) | retrans ref held |
| L2897 | success (default: SYN_SENT, FIN_WAIT2, OFFLOADED, MPAREQ_RCVD, UNKNOWN) | NO (none) | YES (irdma_cleanup_retrans_entry at L2893) | ❌ EXCESS PUT | no retrans entry exists in these states → refcount underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`irdma_cleanup_retrans_entry` at line 2893 in the default case covers states that never created a retrans entry (SYN_SENT, FIN_WAIT2, OFFLOADED, etc.), so calling a put (which decrements cm_node->refcnt) without a corresponding get causes a refcount excess put.
```
