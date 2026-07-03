# REAL BUG: net/ceph/osd_client.c:3974 scan_requests()

**Confidence**: LOW | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

excess put` inside `check_linger_pool_dne` at line 3974. The lreq’s refcount at this point may be too low (e.g., tree reference already dropped by `recalc_linger_target`) leading to double‑put, or `check_linger_pool_dne` unconditionally releases a non‑existent reference. Requires callee source. |

## Full Response

```
[NEED_SOURCE] check_linger_pool_dne
[NEED_SOURCE] recalc_linger_target

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3947 (CALC_TARGET_NO_ACTION, no force_resend) | void (loop continues) | N/A (no get) | N/A | ✅ | No refcount operations. |
| L3947 (CALC_TARGET_NO_ACTION, fallthrough to NEED_RESEND) | void (loop continues) | get via cancel_linger_map_check? (contract says ling_put) → implicit get must have existed for map check reference | cancel_linger_map_check does ling_put | ✅ (if map check reference held) | Balanced if an active map check reference was held. |
| L3952 (CALC_TARGET_NEED_RESEND) | void | (same as above) | cancel_linger_map_check (put) | ✅ | Same. |
| L3955 (CALC_TARGET_POOL_DNE) | void (loop continues) | No explicit get before call; lreq holds tree reference + possibly map check reference. `check_linger_pool_dne` is called; its internal puts may underflow. | check_linger_pool_dne does puts (unknown number) | ❓ (potential underflow) | Smatch warns of `refcount excess put` inside `check_linger_pool_dne` at line 3974. The lreq’s refcount at this point may be too low (e.g., tree reference already dropped by `recalc_linger_target`) leading to double‑put, or `check_linger_pool_dne` unconditionally releases a non‑existent reference. Requires callee source. |

VERDICT: REAL_BUG
CONFIDENCE: LOW
`check_linger_pool_dne` triggers an excess put on the `lreq` kref, likely because a prior action (e.g., `recalc_linger_target` when pool DNE) already dropped the tree reference, or because `check_linger_pool_dne` drops a reference (like a map check reference) that isn’t held in this case. Without callee sources the exact imbalance cannot be confirmed, but the smatch underflow warning points to a real refcounting error.

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] check_linger_pool_dne
[NEED_SOURCE] do_cancel_linger_map_check

`recalc_linger_target` itself has no explicit get/put operations on the lreq refcount, only tree linkage changes. To perform the mandatory path table for `do_cancel_linger_map_check` (the function where the refcount underflow warning occurs at line 3974), its full source and the source of `check_linger_pool_dne` are required. Without them, the exact reference counts and operation ordering cannot be verified.

--- [NEED_SOURCE r2] ---

[NEED_SOURCE] do_cancel_linger_map_check
[NEED_SOURCE] check_linger_pool_dne

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3974 (caller) | void | Unknown (no source) | Excess put via `check_linger_pool_dne` | ❌ Underflow | Smatch warns of `refcount excess put '&lreq->kref'` inside `do_cancel_linger_map_check` at this line. Without source, the exact get/put pairs cannot be enumerated; the caller may have already dropped a needed reference or `check_linger_pool_dne` drops a reference not held. The warning itself indicat
```
