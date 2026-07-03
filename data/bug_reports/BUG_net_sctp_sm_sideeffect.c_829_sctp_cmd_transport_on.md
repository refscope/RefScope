# REAL BUG: net/sctp/sm_sideeffect.c:829 sctp_cmd_transport_on()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

: may or may not call `sctp_transport_hold` | **Yes** (unconditional `sctp_transport_put` inside `sctp_transport_immediate_rtx`) | If GET=YES → balanced; **if GET=NO → PUT without GET → refcount underflow** | **Excess put on path 2 when `sctp_transport_reset_hb_timer` does NOT hold a reference** |

## Full Response

```
| Path | Condition | GET (sctp_transport_reset_hb_timer) | PUT (sctp_transport_immediate_rtx) | Balanced? | Notes |
|------|-----------|-------------------------------------|-----------------------------------|-----------|-------|
| 1 | `!(was_unconfirmed && transport_count == 1)` – immediate_rtx not called | Conditional: may or may not call `sctp_transport_hold` | No | If GET happened → unbalanced (leak), if GET did not happen → balanced |  |
| 2 | `was_unconfirmed && transport_count == 1` – immediate_rtx called | Conditional: may or may not call `sctp_transport_hold` | **Yes** (unconditional `sctp_transport_put` inside `sctp_transport_immediate_rtx`) | If GET=YES → balanced; **if GET=NO → PUT without GET → refcount underflow** | **Excess put on path 2 when `sctp_transport_reset_hb_timer` does NOT hold a reference** |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`sctp_transport_reset_hb_timer()` conditionally increments the refcount, but `sctp_transport_immediate_rtx()` unconditionally decrements it; when the reset function does not hold a reference and the `was_unconfirmed && transport_count == 1` condition is true, an excess put at line 829 occurs.
```
