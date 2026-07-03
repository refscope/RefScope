# REAL BUG: drivers/infiniband/hw/irdma/cm.c:3132 irdma_cm_close()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

ef_cm_node` (a `refcount_dec_and_test` put) for states MPAREJ_RCVD, UNKNOWN, INITED, CLOSED, LISTENER_DESTROYED, and OFFLOADED. If the node already has a zero refcount in these states (e.g., already closed), this triggers `refcount_excess_put`. The smatch warning confirms a run‑time underflow.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3112 (FIN_WAIT1, FIN_WAIT2, LAST_ACK, TIME_WAIT, CLOSING) | return -EINVAL | NO | NO | ✅ | No get/put in this path. |
| L3102 (SYN_RCVD, SYN_SENT, ONE_SIDE_ESTABLISHED, ESTABLISHED, ACCEPTING, MPAREQ_SENT, MPAREQ_RCVD) | break → return 0 | NO | NO | ✅ | Cleans retrans, sends reset; no put. |
| L3116 (LISTENING) | break → return 0 | NO | NO | ✅ | Cleans retrans, sends reset; no put. |
| L3106 (CLOSE_WAIT) | break → return 0 | NO | NO | ✅ | Sends fin only; no put. |
| L3123 (MPAREJ_RCVD, UNKNOWN, INITED, CLOSED, LISTENER_DESTROYED) | break → return 0 | NO | **YES** (irdma_rem_ref_cm_node) | ❌ EXCESS PUT | `irdma_rem_ref_cm_node` releases a reference but no get was performed inside `irdma_cm_close`. If caller held no reference (e.g., node already CLOSED, refcount 0), this causes a refcount underflow. |
| L3129 (OFFLOADED) | break → return 0 | NO | **YES** (irdma_rem_ref_cm_node) | ❌ EXCESS PUT | Same as above – unconditional put without local get. |
| L3132 (return 0, after any break) | return 0 | N/A | N/A | N/A | Fallthrough from the above paths; the excess put already happened in the PUT paths. |

**Pre-Verdict Checklist:**
1. **“Held for device lifetime”?** No – this is per-connection cm_node, not a probe resource.  
2. **“Ownership transferred”?** No – `irdma_cm_close` directly calls the put without any transfer mechanism.  
3. **Unconditional GET?** Not applicable – there is **no get** inside this function, but the warning is about an *excess put*, meaning a put without a prior get.  
4. **goto out between GET and PUT?** No goto constructs here.

The function unconditionally calls `irdma_rem_ref_cm_node` (a `refcount_dec_and_test` put) for states MPAREJ_RCVD, UNKNOWN, INITED, CLOSED, LISTENER_DESTROYED, and OFFLOADED. If the node already has a zero refcount in these states (e.g., already closed), this triggers `refcount_excess_put`. The smatch warning confirms a run‑time underflow.

```
VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
```
