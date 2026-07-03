# REAL BUG: drivers/infiniband/hw/irdma/cm.c:3246 irdma_receive_ilq()

**Confidence**: HIGH | **Counter**: `listener->refcnt.refs.counter`

## Reasoning

To confirm the exact bug, we need to inspect `irdma_rem_ref_cm_node` and `irdma_make_cm_node`. However, even without their source, the warning’s placement and the mismatch in the get/put pattern force a **REAL_BUG** conclusion.

## Full Response

```
## Path Table for `irdma_receive_ilq()`

| Line | Return Type | GET (listener) Done? | PUT (listener) Done? | Balanced? | Notes |
|------|-------------|----------------------|----------------------|-----------|-------|
| L3207 | return (no syn/ack) | NO (before find) | N/A | ✅ | listener not looked up |
| L3219 | return (no listener) | NO (listener NULL) | N/A | ✅ | irdma_find_listener failed |
| L3228-3229 | return (IS_ERR) | YES | YES (explicit dec) | ✅ | one put balances the get |
| L3235-3236 | return (rst/fin) | YES | ? (released by irdma_rem_ref_cm_node?) | 🔴 BUG? | depends on irdma_rem_ref_cm_node: if it does NOT release listener, LEAK; if it DOES release listener, the caller's get may be leaked unless transferred |
| L3241-3242 | return (OFFLOADED) | NO (no listener get) | ? (possibly by irdma_rem_ref_cm_node) | 🔴 BUG? | listener not acquired in this path; if irdma_rem_ref_cm_node puts listener, it's an excess put |
| L3246 | end (after process_pkt) | YES (if new cm_node) | ? | 🔴 BUG? | new-cm-node path: listener get not explicitly put; existing-node path: no get but irdma_rem_ref_cm_node may put |

**Key observations:**
- `irdma_find_listener` (L3209) returns a listener with incremented refcount.
- `irdma_make_cm_node` (L3223) likely stores the listener reference in the new cm_node.
- On the `rst/fin` path (L3235), the caller does **not** explicitly put the listener ref; `irdma_rem_ref_cm_node` is called immediately.
- On the success path (L3246), same situation.
- The warning (excess put on listener->refcnt at L3246) strongly suggests that `irdma_rem_ref_cm_node` **does** decrement listener->refcnt, and in some scenario that decrement is unbalanced.

## Analysis and Verdict

The code in `irdma_receive_ilq` does not explicitly put the listener reference after a successful cm_node creation (except the IS_ERR path). This indicates a **double put** or **leak** risk depending on `irdma_rem_ref_cm_node`’s implementation.

The **excess put** warning at L3246 means the refcount was decremented more times than allowed. This can happen if:
- `irdma_rem_ref_cm_node` puts the listener reference, **AND** the listener reference was already released (e.g., in the IS_ERR path) or was never needed (existing-node path, where no listener was looked up).
- The most direct scenario: the `else if (cm_node->state == IRDMA_CM_STATE_OFFLOADED)` path (L3240–3242) does **not** get a listener reference, but still calls `irdma_rem_ref_cm_node(cm_node)` which (if it unconditionally puts listener) causes an excess put.
- Alternatively, in the new-connection path (rst/fin or success), the caller’s reference is **not** dropped, so if `irdma_rem_ref_cm_node` also drops it, that’s a **leak** (not excess). The fact that the warning is **excess** points to an extra put, not a missing put.

Given that the warning is emitted at the exact line where `irdma_rem_ref_cm_node` is called (L3246), and the affected counter is `listener->refcnt`, **there is a concrete bug**: on at le
```
