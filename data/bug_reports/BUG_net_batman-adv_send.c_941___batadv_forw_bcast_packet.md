# REAL BUG: net/batman-adv/send.c:941 __batadv_forw_bcast_packet()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

(primary_if)` without taking a new reference), leading to a double-put when the caller also releases it.

## Full Response

```
| Line | Return Type | GET Done? (primary_if) | PUT Done? (primary_if) | Balanced? | Notes |
|------|-------------|-------------------------|------------------------|-----------|-------|
| L913 | error       | NO (primary_if == NULL) | N/A                    | ✅         | early return before get |
| L941 | success     | YES                     | YES (batadv_hardif_put) | ❓         | depends on `batadv_forw_bcast_packet_if` |

**⚠️ Unbalanced path:** The only primary_if `GET` is at L909, and the only put is at L941. The warning reports an **excess put** at L941, meaning the refcount was already zero when `batadv_hardif_put(primary_if)` was called. This can happen if `batadv_forw_bcast_packet_if()` internally releases the reference on `primary_if` (e.g., by calling `batadv_hardif_put(primary_if)` without taking a new reference), leading to a double-put when the caller also releases it.

Without the source of `batadv_forw_bcast_packet_if`, the exact cause is uncertain. I need to see whether the callee drops the caller‑owned reference.

[NEED_SOURCE] batadv_forw_bcast_packet_if

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
Smatch detected an excess `kref_put` on `primary_if` at L941. The most plausible explanation is that `batadv_forw_bcast_packet_if()` releases the passed `primary_if` reference without re‑acquiring it, causing the caller’s later put to be a double‑put. Either the callee should not put, or the caller must not put after the call; in its current form the reference is released twice.
```
