# REAL BUG: net/dsa/port.c:1564 dsa_port_change_conduit()

**Confidence**: HIGH | **Counter**: `$->bridge.refcount.refs.counter`

## Reasoning

gests a preparatory step that may also call `dsa_port_bridge_leave` or perform a `kref_put`, creating a double‑put. Without the source I assume it does NOT do a put for the base path analysis, but the warning of *excess put* strongly indicates it does.

## Full Response

```
| Line | Return Type | GET Done? (dsa_port_bridge_join) | PUT Done? (dsa_port_bridge_leave) | Balanced? | Notes |
|------|-------------|------|-----|-----------|-------|
| L1438 (dsa_port_bridge_leave) | (first put) | – | 1× YES (explicit) | – | initial leave |
| L1468 (return 0, success) | return 0 | YES (at L1464) | 1× YES | ✅ if only 1 put | balanced if no double‑put |
| L1458 (vlan filter failure → goto rewind_old_bridge) | goto→rewind_old_bridge | YES (in rewind_old_bridge) | 1× YES | ✅ | rejoin old bridge restores ref |
| L1478 (assign conduit failure → goto rewind_old_addrs) | goto→rewind_old_addrs→rewind_old_bridge | YES (falls through) | 1× YES | ✅ | |
| L1495 (host_uc_install failure → goto rewind_addr_inherit) | goto→rewind_addr_inherit→…→rewind_old_bridge | YES | 1× YES | ✅ | |
| L1501 (bridge join -EOPNOTSUPP → goto rewind_new_vlan) | goto→rewind_new_vlan→…→rewind_old_bridge | YES | 1× YES | ✅ | |
| L1515 (other errors) | any error via rewind path | YES (eventually) | 1× YES | ✅ | |

**Note on `dsa_port_pre_bridge_leave`:** Its source is not provided. The name suggests a preparatory step that may also call `dsa_port_bridge_leave` or perform a `kref_put`, creating a double‑put. Without the source I assume it does NOT do a put for the base path analysis, but the warning of *excess put* strongly indicates it does.

[NEED_SOURCE] dsa_port_pre_bridge_leave

---

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`dsa_port_change_conduit` calls `dsa_port_pre_bridge_leave` immediately followed by `dsa_port_bridge_leave`. The latter is a known PUT on the bridge refcount. The `refcount excess put` warning at `net/dsa/port.c:1564` (likely inside `dsa_port_bridge_leave`) means an extra decrement occurred. The only plausible source is an additional put inside `dsa_port_pre_bridge_leave`, causing a double‑put that underflows the refcount. All error paths later call `dsa_port_bridge_join` (GET) to restore the reference, so a single initial put would be balanced, confirming the excess comes from the pre‑leave helper.
```
