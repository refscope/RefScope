# REAL BUG: net/sctp/sm_sideeffect.c:626 sctp_do_8_2_transport_strike()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

- Because the pf_enable condition and the DOWN condition are independent, a path where the pf_enable condition is false **and** the DOWN condition is true results in a PUT without any GET → refcount underflow.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L626 (sctp_assoc_control_transport(DOWN)) | implicit (end of function) | NO (no get on this path if pf_enable condition is false) | YES (internal put) | ❌ EXCESS PUT | refcount went negative – no matching get |
| L582 (sctp_assoc_control_transport(PF)) | implicit (end of function) | YES (via sctp_transport_reset_hb_timer at L584) | YES (PF put) | ⚠️ put then get, but refcount may remain unchanged | tool flags only L626 as excess |
| End (no DOWN or PF condition hit) | implicit (end of function) | NO | NO | ✅ | no refcount operations |

- The **DOWN** path at L626 includes a PUT unconditionally (inside sctp_assoc_control_transport).  
- No preceding GET exists for the transport on that path, unless the pf_enable block also executed.  
- The pf_enable block contains a GET (via sctp_transport_reset_hb_timer, which conditionally calls sctp_transport_hold) **after** its own PUT.  
- Because the pf_enable condition and the DOWN condition are independent, a path where the pf_enable condition is false **and** the DOWN condition is true results in a PUT without any GET → refcount underflow.

## Verdict

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

sctp_do_8_2_transport_strike calls sctp_assoc_control_transport(SCTP_TRANSPORT_DOWN) at line 626, which performs a put on the transport’s refcnt. In the common path where the pf_enable block is not entered, no corresponding get is performed, causing the refcount to go below zero (excess put).
```
