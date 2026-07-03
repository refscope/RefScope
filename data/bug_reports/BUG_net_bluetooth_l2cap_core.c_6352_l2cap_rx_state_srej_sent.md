# REAL BUG: net/bluetooth/l2cap_core.c:6352 l2cap_rx_state_srej_sent()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| EV_RECV_SREJ | 0 | l2cap_handle_srej() (PUT) | ✅ | |

## Full Response

```
| Path (Event & Sub‑condition) | GETs (chan kref) | PUTs (chan kref) | Balanced? | Notes |
|------------------------------|------------------|------------------|-----------|-------|
| EV_RECV_IFRAME / EXPECTED (L6225‑6233) | 0 | l2cap_pass_to_tx() | ✅ (net –1) | Caller reference dropped |
| EV_RECV_IFRAME / EXPECTED_SREJ (L6234‑6246) | 0 | l2cap_pass_to_tx() (+ maybe l2cap_rx_queued_iframes) | ✅ (net –1) | |
| EV_RECV_IFRAME / UNEXPECTED (L6247‑6258) | 0 | l2cap_pass_to_tx() | ✅ | |
| EV_RECV_IFRAME / UNEXPECTED_SREJ (L6259‑6271) | 0 | l2cap_pass_to_tx() | ✅ | |
| EV_RECV_IFRAME / DUPLICATE_SREJ (L6272‑6275) | 0 | l2cap_pass_to_tx() | ✅ | |
| EV_RECV_IFRAME / DUPLICATE (L6276‑6280) | 0 | 0 | ⚠️ No drop (possible leak, not excess put) | |
| EV_RECV_IFRAME / INVALID_IGNORE (L6281‑6282) | 0 | 0 | ⚠️ | |
| EV_RECV_IFRAME / INVALID/DEFAULT (L6283‑6286) | 0 | l2cap_send_disconn_req() (PUT, but may not be on chan kref) | ❓ | Unclear ref target |
| **EV_RECV_RR / final & !CONN_REJ_ACT** (L6289‑6300) | 0 | **l2cap_pass_to_tx()** (L6290) **+ l2cap_retransmit_all()** (L6297) | **❌ DOUBLE PUT** | **Excess put on chan kref** |
| EV_RECV_RR / final & CONN_REJ_ACT already set | 0 | l2cap_pass_to_tx() | ✅ | |
| EV_RECV_RR / poll, __set_retrans_timer called | 1 (__set_retrans_timer) | l2cap_pass_to_tx() | ✅ (approx) | get offsets pass_to_tx |
| EV_RECV_RR / poll, no __set_retrans_timer | 0 | l2cap_pass_to_tx() (+ maybe l2cap_send_srej_tail) | ❓ | |
| EV_RECV_RR / else (not final, not poll) | 1 (possibly +1 from __set_retrans_timer) +1 (l2cap_send_ack) | l2cap_pass_to_tx() | ✅ (net ≥ 0) | No excess put |
| **EV_RECV_RNR / else** (L6319‑6331) | 0 | **l2cap_pass_to_tx()** (L6321) **+ l2cap_send_sframe()** (L6330) | **❌ DOUBLE PUT** | **Excess put** |
| EV_RECV_RNR / poll | 0 | l2cap_pass_to_tx() + l2cap_send_srej_tail() (unknown) | ❓ | |
| EV_RECV_REJ | 0 | l2cap_handle_rej() (PUT) | ✅ | |
| EV_RECV_SREJ | 0 | l2cap_handle_srej() (PUT) | ✅ | |

**VERDICT**: REAL_BUG  
**CONFIDENCE**: MEDIUM  
**Reason**: Two paths (L2CAP_EV_RECV_RR with final and !CONN_REJ_ACT, L2CAP_EV_RECV_RNR else) call both `l2cap_pass_to_tx()` (PUT) and a second PUT function (`l2cap_retransmit_all()` or `l2cap_send_sframe()`) without an intervening GET. Both target the channel’s `kref`, leading to an excess put.
```
