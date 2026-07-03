# REAL BUG: drivers/md/bcache/btree.c:1693 btree_gc_recurse()

**Confidence**: MEDIUM | **Counter**: `$->c->prio_blocked.counter`

## Reasoning

4. **`goto out` between GET and PUT?** – Not applicable; the imbalance stems from the order of operations: PUT is called *before* the possibly compensating GET.

## Full Response

```
## Path Table for `btree_gc_recurse()`

| Line Range | Return / Exit Path | GET (rewrite_node) Done? | PUT (coalesce) Done? | Balanced? | Notes |
|------------|---------------------|--------------------------|----------------------|-----------|-------|
| 1628‑1629 | `bch_btree_node_get` returns ERR → `break` → cleanup → return | NO (never reached) | NO (coalesce not called) | ✅ | |
| 1635‑1636 | `btree_gc_coalesce` returns error → `break` → return | NO (rewrite after coalesce) | YES | ❌ **EXCESS PUT** | coalesce put without matching get from rewrite_node |
| 1639‑1640 | `!last->b` → `break` → return (coalesce already called if `k` was processed) | NO (rewrite block skipped) | YES (if `k` fetched) | ❌ **EXCESS PUT** (if coalesce happened) | only if previous iteration had a successful `k` |
| 1646‑1647 | `btree_gc_rewrite_node` fails → `break` → return | NO (rewrite failed, no get effect) | YES (coalesce succeeded earlier) | ❌ **EXCESS PUT** | rewrite_node might not have updated counter on failure |
| 1652‑1653 | `btree_gc_recurse` fails → `break` → return | YES (rewrite succeeded before recursion) | YES (coalesce done earlier) | ✅ | GW: rewrite_node did get, coalesce did put – matched if both succeeded |
| 1674‑1675 | node count → `-EAGAIN; break` → return | YES (rewrite OK) | YES (coalesce OK) | ✅ | |
| 1679‑1680 | `need_resched` → `-EAGAIN; break` → return | YES (rewrite OK) | YES (coalesce OK) | ✅ | |
| 1693 (end) | normal loop exit + cleanup → `return ret` | YES (final iteration done) | YES (final iteration done) | ✅ | |

**Key observation:** Lines 1635‑1636, 1639‑1640 (when `k` was fetched), and 1646‑1647 represent paths where `btree_gc_coalesce` (the PUT) has been called, but `btree_gc_rewrite_node` (the GET) has **not** executed or not completed successfully. This yields a net decrement on `c->prio_blocked.counter`, an excess put.

---

## Pre‑Verdict Checklist

1. **“Held for device lifetime”?** – n/a; this is a counter mismatch.
2. **“Ownership transferred”?** – No evidence that coalesce/rewrite transfer ownership of the counter; the counter is global to the cache_set.
3. **Unconditional GET?** – `btree_gc_rewrite_node` is the GET; it is only called conditionally (`should_rewrite`). The PUT (`btree_gc_coalesce`) is unconditional after a successful node get.
4. **`goto out` between GET and PUT?** – Not applicable; the imbalance stems from the order of operations: PUT is called *before* the possibly compensating GET.

---

## VERDICT: REAL_BUG

**CONFIDENCE: MEDIUM**  
(Calic source not provided, but the contract directions – GET in `btree_gc_rewrite_node`, PUT in `btree_gc_coalesce` – and the execution order in the loop make the imbalance directly inferable: `btree_gc_coalesce` is called before `btree_gc_rewrite_node`, and many break paths skip the subsequent get, leading to an excess decrement of `prio_blocked.counter`.)
```
