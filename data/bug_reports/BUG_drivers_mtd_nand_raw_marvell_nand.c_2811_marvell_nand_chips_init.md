# REAL BUG: drivers/mtd/nand/raw/marvell_nand.c:2811 marvell_nand_chips_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

4. `goto out` blind spot — not present.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2789 | error (-EINVAL) | NO (before any DT node iteration) | N/A | ✅ | No `device_node` accessed |
| L2798 | legacy return ret | MAYBE (legacy path uses `np`, not scoped loop) | N/A | N/A | Not relevant to warning; no scoped double‑put risk |
| L2805 | error (loop body after `marvell_nand_chip_init` failure) | YES (scoped `for_each_child_of_node_scoped` obtains a reference for `nand_np`) | YES **twice**: once via `marvell_nand_chips_cleanup` (puts chip’s stored node) **and** once via the scoped `__cleanup__` attribute that calls `of_node_put(nand_np)` | ❌ **EXCESS PUT** | Double `of_node_put` on the same `device_node` → refcount underflow |
| L2809 | success (return 0) | YES (all child nodes iterated, final node put by scoped cleanup) | YES (only the scoped `__cleanup__` put) | ✅ | Chips hold their own extra references; scoped put does not conflict |

## Analysis

- The function uses `for_each_child_of_node_scoped(np, nand_np)`, which auto‑releases the `nand_np` reference on scope exit via `__cleanup__(of_node_put)`.
- On error, `marvell_nand_chips_cleanup(nfc)` is called **before** the return. This function walks already‑initialised chips and calls `of_node_put(chip->dn)` on each.
- Inside `marvell_nand_chip_init()`, the child DT node pointer is preserved (e.g., after `of_node_get(nand_np)`) so the chip holds an extra reference. Thus `marvell_nand_chips_cleanup` releases that reference.
- After the cleanup returns, the scoped auto‑cleanup still fires, issuing another `of_node_put(nand_np)` on the same node. This second put works on an already‑released reference → **refcount excess put** (underflow) exactly as warned.
- The success path avoids double‑put because it never calls `marvell_nand_chips_cleanup`; the chip’s reference is released later during normal device removal.

**Pre‑verdict checklist:**
1. “Held for device lifetime” — not applicable; error path is pre‑probe.  
2. Ownership transfer — chip init takes a reference, but cleanup drops it; the scoped variable still holds its own reference that must be released; the two are independent, so no transfer that would cancel the scoped put.  
3. Unconditional GET — `of_get_next_child` always increments; the macro’s get is unconditional → the scoped put must always happen.  
4. `goto out` blind spot — not present.

## VERDICT: REAL_BUG

## CONFIDENCE: HIGH

`marvell_nand_chips_cleanup` plus the auto‑cleanup from `for_each_child_of_node_scoped` put the same `device_node` twice on error path.
```
