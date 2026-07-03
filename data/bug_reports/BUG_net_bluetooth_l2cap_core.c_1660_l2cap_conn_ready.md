# REAL BUG: net/bluetooth/l2cap_core.c:1660 l2cap_conn_ready()

**Confidence**: LOW | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

- Without the full lifecycle of `chan->kref` across multiple invocations of `l2cap_conn_ready`, the exact bug cannot be confirmed, but the asymmetry strongly suggests an extra `kref_put` without a corresponding `kref_get`.

## Full Response

```
| Path (branch) | GET Done? | PUT Done? | Balanced? | Notes |
|---------------|-----------|-----------|-----------|-------|
| LE_LINK (hcon->type == LE_LINK) → l2cap_le_start(chan) | unknown (callee semantics not provided) | unknown | unknown | l2cap_le_start contract missing; may include PUT |
| !LE_LINK && chan->chan_type != L2CAP_CHAN_CONN_ORIENTED && info_state flag set → l2cap_chan_ready(chan) | NO (no kref_get in this function on this path) | YES (l2cap_chan_ready → __clear_chan_timer → kref_put) | **❌ POTENTIAL EXCESS PUT** | Channel’s kref may already be 1 from creation, but if flag already set, repeated calls would cause double put |
| !LE_LINK && chan->state == BT_CONNECT → l2cap_do_start(chan) | likely YES (name suggests kref_get) | NO | balanced only if later put exists elsewhere | |
| other cases (no-op) | N/A | N/A | N/A | |

**Additional notes**:  
- The function has a single exit; all branches converge to `queue_work`. No early returns.  
- The only explicit PUT in the function is via `l2cap_chan_ready` when the conditions above are met.  
- The GET for the same channel never happens inside this function on that path — `l2cap_do_start` is only called when `state == BT_CONNECT`, not on the `!ORIENTED` path.  
- The warning “refcount excess put” points to line 1660 (likely the `l2cap_chan_ready` call site), indicating the reference count was decremented too far (possibly from zero).  
- Without the full lifecycle of `chan->kref` across multiple invocations of `l2cap_conn_ready`, the exact bug cannot be confirmed, but the asymmetry strongly suggests an extra `kref_put` without a corresponding `kref_get`.

VERDICT: REAL_BUG  
CONFIDENCE: LOW  

The asymmetry between `l2cap_chan_ready` (PUT) on the non‑connection‑oriented path and the absence of any GET on that path means the call can cause an excess put if the channel’s info‑state flag is already set, leading to refcount underflow. More context (`l2cap_chan_ready`, `l2cap_do_start`, `l2cap_le_start` sources) is needed for high confidence.
```
