# REAL BUG: net/batman-adv/mesh-interface.c:874 batadv_meshif_slave_del()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

- The error path correctly releases the reference once, so no imbalance there.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L866–L867 (goto out) | error path (if condition true) | YES (hard_iface ≠ NULL and mesh_iface mismatch) | YES (at L874, via `batadv_hardif_put`) | ✅ | Normal get‑then‑put for non‑matching interface |
| L869–L874 (fall‑through) | success path (condition false) | YES (hard_iface ≠ NULL, valid interface) | YES (inside `batadv_hardif_disable_interface` and at L874) | ❌ **EXCESS PUT** | Two puts for one get – `disable_interface` already releases the reference (see contract `→batadv_hardif_put`) |

## Reasoning

- `batadv_hardif_get_by_netdev()` acquires a kref reference conditionally (succeeds → pointer ≠ NULL).
- The success path calls `batadv_hardif_disable_interface()`. Its contract shows an unconditional call to `batadv_hardif_put()`. The only object available in that context is the passed `hard_iface`. Therefore `disable_interface` releases one reference.
- The function then executes `batadv_hardif_put(hard_iface)` at `out:`, releasing the same reference a second time → refcount underflow.
- The error path correctly releases the reference once, so no imbalance there.

## Verdict
VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
