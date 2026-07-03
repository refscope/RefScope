# REAL BUG: drivers/scsi/scsi_transport_iscsi.c:3097 iscsi_if_ep_disconnect()

**Confidence**: HIGH | **Counter**: `ep->dev.kobj.kref.refcount.refs.counter`

## Reasoning

_put_endpoint(ep)` at L3095, return 0 | YES (ep non‑NULL) | YES (L3095) **but callee also puts** | ❌ EXCESS | `iscsi_if_disconnect_bound_ep` contract says it can call `iscsi_put_endpoint` conditionally; the explicit put at L3095 creates a double‑put → refcount goes negative → warning at L3097 |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3072 | early return (`!transport->ep_disconnect`) | NO (before get) | N/A | ✅ | |
| L3077 | `ep==NULL` return `-EINVAL` | NO (get failed) | N/A | ✅ | `iscsi_lookup_endpoint` returns NULL → no ref taken |
| L3086 → L3095 | `conn == NULL`: `transport->ep_disconnect(ep)`, `goto put_ep`, `iscsi_put_endpoint(ep)` at L3095, return 0 | YES (ep non‑NULL) | YES (L3095) | ✅ | Single put after get |
| L3092 → L3095 | `conn != NULL`: `iscsi_if_disconnect_bound_ep(conn, ep, false)`, fall‑through to `put_ep`, `iscsi_put_endpoint(ep)` at L3095, return 0 | YES (ep non‑NULL) | YES (L3095) **but callee also puts** | ❌ EXCESS | `iscsi_if_disconnect_bound_ep` contract says it can call `iscsi_put_endpoint` conditionally; the explicit put at L3095 creates a double‑put → refcount goes negative → warning at L3097 |

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH

The contract for `iscsi_if_disconnect_bound_ep` states it may call `iscsi_put_endpoint` (conditional_on_path). On the `conn != NULL` path, the function is invoked, and afterwards the caller unconditionally calls `iscsi_put_endpoint(ep)` at the `put_ep` label (line 3095). This causes a double release of the device reference obtained by `iscsi_lookup_endpoint`, resulting in the reported “refcount excess put”. The fix is to remove the `iscsi_put_endpoint(ep)` after `iscsi_if_disconnect_bound_ep` returns, or to ensure that `iscsi_if_disconnect_bound_ep` does not drop the reference when called with the given arguments.
```
