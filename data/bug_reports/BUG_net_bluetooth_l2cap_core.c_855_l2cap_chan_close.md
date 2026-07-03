# REAL BUG: net/bluetooth/l2cap_core.c:855 l2cap_chan_close()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

*(To confirm whether these functions already call kref_put / l2cap_chan_del.)*

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L817 | break (BT_LISTEN) | NO (no get call) | NO (no put visible) | ✅ | teardown() may handle ref, not kref |
| L824 | break (BT_CONNECTED/CONFIG, CONN_ORIENTED) | YES (__set_chan_timer → l2cap_chan_hold) | YES (l2cap_send_disconn_req) | ✅ | get + put balanced |
| L826 | break (BT_CONNECTED/CONFIG, else) | NO (no get) | YES (l2cap_chan_del) | ✅ | single put releases reference, expected |
| **L832 → L845** | break (BT_CONNECT2, CONN_ORIENTED, ACL_LINK) | **UNCERTAIN** | **YES (l2cap_chan_del)** | **❓** | If `l2cap_chan_connect_reject()` already puts, double put → excess. Otherwise balanced. |
| **L836 → L845** | break (BT_CONNECT2, CONN_ORIENTED, LE_LINK, MODE_LE_FLOWCTL) | **UNCERTAIN** | **YES (l2cap_chan_del)** | **❓** | If `l2cap_chan_le_connect_reject()` already puts, double put → excess. |
| L839‑L840 | return (BT_CONNECT2, CONN_ORIENTED, LE_LINK, MODE_EXT_FLOWCTL) | NO (no get) | NO (no l2cap_chan_del) | ✅ | `l2cap_chan_ecred_connect_reject()` may put, but no extra put; balanced if reject does the sole put. |
| L845 | break (BT_CONNECT2, not CONN_ORIENTED or type fallthrough) | NO | YES (l2cap_chan_del) | ✅ | single put, normal |
| L850 | break (BT_CONNECT/DISCONN) | NO | YES (l2cap_chan_del) | ✅ | single put, normal |
| L854 | break (default) | NO | NO | ✅ | teardown() likely no kref |

**Legend:**  
- **GET** = refcount increment (kref_get / l2cap_chan_hold)  
- **PUT** = refcount decrement (kref_put / equivalent in l2cap_chan_del / l2cap_send_disconn_req)  
- ⚠️ Highlighted rows are suspect for excess put. The `l2cap_chan_del()` at L845 after a reject function that already releases the reference would cause an extra put → refcount underflow.

## Analysis

1. **The warning is “refcount excess put”** – the put at line 855 (likely the `l2cap_chan_del` at L845 in BT_CONNECT2) causes the refcount to drop below zero.
2. **The BT_CONNECT2 case** for **CONN_ORIENTED ACL_LE or LE_FLOWCTL** calls a reject function (`l2cap_chan_connect_reject` / `l2cap_chan_le_connect_reject`) and then falls through to the unconditional `l2cap_chan_del`.
3. **Reject functions in Bluetooth typically clean up the channel**, including releasing the kref. If they already call `l2cap_chan_del` or `kref_put`, then the subsequent `l2cap_chan_del` at L845 is a **double put**, exactly matching the excess put warning.
4. The **EXT_FLOWCTL** path does not have this problem because it returns immediately after the reject, skipping the extra `l2cap_chan_del`.
5. No IS_ERR guards, devm cleanup, or async deferral apply here – the error is purely a duplicate release.

Missing source prevents absolute verification, but the code pattern and warning strongly indicate a double put.

## [NEED_SOURCE] l2cap_chan_connect_reject
## [NEED_SOURCE] l2cap_chan_le_connect_reject
## [NEED_SOURCE] l2cap_chan_ecred_connect_reject

*(To confirm whet
```
