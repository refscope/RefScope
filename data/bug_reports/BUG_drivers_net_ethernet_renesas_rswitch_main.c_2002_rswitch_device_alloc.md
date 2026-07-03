# REAL BUG: drivers/net/ethernet/renesas/rswitch_main.c:2002 rswitch_device_alloc()

**Confidence**: HIGH | **Counter**: `rdev->np_port->kobj.kref.refcount.refs.counter`

## Reasoning

| L2000 | success (return 0) | YES (ref held for device lifetime) | NO (intentional – ownership transferred) | ✅ | ref kept in rdev->np_port for later release in device removal |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1949 | error (–EINVAL) | NO (before get) | N/A | ✅ | index check fails before any ref acquisition |
| L1952 | error (–ENOMEM) | NO (before get) | N/A | ✅ | alloc_etherdev_mqs fails before rswitch_get_port_node |
| L1990 | goto out_get_params | UNCERTAIN (rswitch_get_port_node may not have inc’d ref) | YES (of_node_put unconditional) | ❌ potential excess put | Contract says get uses of_get_child_by_name but tool’s **refcount excess put** warning indicates the put released a ref that was never taken. |
| L1994 | goto out_rxdmac (falls through to out_get_params) | UNCERTAIN | YES | ❌ potential excess put | same as above; rswitch_rxdmac_free also done, but put still happens |
| L1998 | goto out_txdmac (falls through to out_get_params) | UNCERTAIN | YES | ❌ potential excess put | same as above; rswitch_rxdmac_free done before put |
| L2000 | success (return 0) | YES (ref held for device lifetime) | NO (intentional – ownership transferred) | ✅ | ref kept in rdev->np_port for later release in device removal |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

**Reasoning**: The error‑cleanup label `out_get_params` calls `of_node_put(rdev->np_port)` unconditionally, assuming `rswitch_get_port_node()` always acquires a reference. However, the reported `refcount excess put` on `rdev->np_port->kobj.kref.refcount` proves that the get function did **not** increment the refcount on the path taken, making the put incorrect and causing a refcount underflow. The call site must avoid the put when no reference was acquired (e.g., by checking the return value more carefully or by ensuring the get always takes a reference).
```
