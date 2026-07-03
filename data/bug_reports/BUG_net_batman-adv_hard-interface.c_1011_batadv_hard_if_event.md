# REAL BUG: net/batman-adv/hard-interface.c:1011 batadv_hard_if_event()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

e)` at `hardif_put` thus becomes a **double-put** (excess put), triggering the refcount warning. The line reported (1011, the `batadv_hardif_put(primary_if)` call) is the immediate location where the underflow is detected after the extra decrement of the same underlying `batadv_hard_iface` object.

## Full Response

```
## Path Table

| Path Description | Return Type | Hard_iface GET? | Hard_iface PUT? | Balanced? | Notes |
|------------------|-------------|-----------------|-----------------|-----------|-------|
| Early meshif valid (L949) | return | N/A | N/A | ✅ | different object |
| hard_iface NULL after get/add (L956→out) | goto out | NO | NO (skips hardif_put) | ✅ | |
| NETDEV_UP → activate → break → hardif_put (L967) | fall-through | YES | YES (at hardif_put) | ❌ EXCESS | `batadv_hardif_activate_interface` internally calls `batadv_hardif_put` (contract) → caller’s `hardif_put` is an **extra put** |
| NETDEV_GOING_DOWN / DOWN (L971) | fall-through | YES | YES (at hardif_put) | ✅ | `batadv_hardif_deactivate_interface` does not release the caller’s reference |
| NETDEV_UNREGISTER / PRE_TYPE_CHANGE (L975) | fall-through | YES | YES (at hardif_put) | ❌ EXCESS | `batadv_hardif_remove_interface` internally calls `batadv_hardif_put` (contract) → extra put |
| NETDEV_CHANGEMTU (L979) | fall-through | YES | YES (at hardif_put) | ✅ | no nested put |
| NETDEV_CHANGEADDR: if_status == NOT_IN_USE → hardif_put (L982) | goto | YES | YES (at hardif_put) | ✅ | primary_if not yet acquired |
| NETDEV_CHANGEADDR: !primary_if → hardif_put (L989) | goto | YES | YES (at hardif_put) | ✅ | no nested put on hard_iface |
| NETDEV_CHANGEADDR: success (L992) | fall-through | YES | YES (at hardif_put) | ✅ | no nested put on hard_iface |
| NETDEV_CHANGEUPPER (L996) | fall-through | YES | YES (at hardif_put) | ✅ | no nested put |
| default (L999) | fall-through | YES | YES (at hardif_put) | ✅ | |

**Key observation**:  
- `batadv_hardif_activate_interface` contract states `→batadv_hardif_put(put)` – it consumes a reference on `hard_iface`.  
- `batadv_hardif_remove_interface` contract states `→batadv_hardif_put(put)` – it also consumes a reference.  
In both these paths the caller’s unconditional `batadv_hardif_put(hard_iface)` at `hardif_put` thus becomes a **double-put** (excess put), triggering the refcount warning. The line reported (1011, the `batadv_hardif_put(primary_if)` call) is the immediate location where the underflow is detected after the extra decrement of the same underlying `batadv_hard_iface` object.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`batadv_hardif_activate_interface` and `batadv_hardif_remove_interface` already put the caller’s reference, so the later `batadv_hardif_put(hard_iface)` in the caller is a refcount excess put.
```
