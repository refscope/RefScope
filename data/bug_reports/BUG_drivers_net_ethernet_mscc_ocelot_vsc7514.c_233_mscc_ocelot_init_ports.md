# REAL BUG: drivers/net/ethernet/mscc/ocelot_vsc7514.c:233 mscc_ocelot_init_ports()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

m `out_teardown`) will attempt to release that reference again, causing a refcount underflow. This is the likely source of the “refcount excess put” warning. The explicit put on the error path should be removed; the reference is now owned by the port subsystem and will be released by its teardown.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L158 | error (-ENOMEM) | NO (before loop) | N/A | ✅ | No node acquired |
| L165 | error (-ENOMEM) | NO (before loop) | N/A | ✅ | No node acquired |
| L191 goto out_teardown | error path | YES (child from loop) | YES (of_node_put at L190) | ✅ | Port not stored; cleanup likely does not touch this node |
| L198 goto out_teardown | error path | YES (child from loop) | YES (of_node_put at L197) | ❌ LEAK/EXCESS PUT | `ocelot_port_devlink_init` may store a reference; cleanup (mscc_ocelot_release_ports) may put again → double put → excess put |
| L218 goto out_teardown | error (unused ports) | NO (no node) | N/A | ✅ | No node involved |
| L223 return 0 | success | YES (all children processed) | Ownership transferred to port structures; put deferred to device removal | ✅ | No double put |

**Reasoning for L198**: After `ocelot_port_devlink_init()` fails, the code explicitly calls `of_node_put(portnp)` and then jumps to `out_teardown`. However, `ocelot_port_devlink_init()` likely allocates a port structure and stores a reference to `portnp` (or transfers ownership). Consequently, the subsequent cleanup via `mscc_ocelot_release_ports()` (called from `out_teardown`) will attempt to release that reference again, causing a refcount underflow. This is the likely source of the “refcount excess put” warning. The explicit put on the error path should be removed; the reference is now owned by the port subsystem and will be released by its teardown.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`of_node_put(portnp)` after `ocelot_port_devlink_init` failure combined with later cleanup in `mscc_ocelot_release_ports` likely produces a double put. Request `[NEED_SOURCE] ocelot_port_devlink_init` and `[NEED_SOURCE] mscc_ocelot_release_ports` for final confirmation.
```
