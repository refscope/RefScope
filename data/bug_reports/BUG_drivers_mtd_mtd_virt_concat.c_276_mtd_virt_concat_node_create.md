# REAL BUG: drivers/mtd/mtd_virt_concat.c:276 mtd_virt_concat_node_create()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

a symptom of the leak confusing the static analysis, but the code **is buggy** because the reference counting is demonstrably incorrect – multiple GETs lack corresponding PUTs. According to the mandatory rule “If ANY row has GET=YES and PUT=NO → REAL_BUG”, this qualifies as a real refcounting bug.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L265 | Loop exit, return ret (0) | YES (for each skipped parts obtained earlier) | NO (no put for skipped nodes) | ❌ LEAK | All `continue` paths after `of_find_node_with_property` leak the reference. The final loop exit when parts==NULL has never put those references. |
| L263 | goto destroy_items (after L262 put) | YES (current parts node) | YES (L262 `of_node_put(parts)`) | ⚠️ DEPENDS ON CALLEE | If `mtd_virt_concat_destroy_items()` also puts the same parts node, double-put. But the `continue`‑path leaks are independent real leaks. |
| L272 | return ret (after destroy_items) | YES (current parts node already put) | N/A (already put) | ❌ LEAK (same as L265, from earlier skipped nodes) | The error path returns with previous skipped nodes still leaked. |

**Decision:** The function unconditionally gets a reference to each device node found by `of_find_node_with_property()` on every loop iteration. The early `continue` statements (`!available`, `mtd_is_part_concat`, `count < MIN_DEV_PER_CONCAT`) **never** release these references before the loop variable `parts` is overwritten with the next node. Consequently, all such skipped nodes suffer a permanent refcount leak. This is a clear violation of the contract that every successful `of_find_node_with_property()` call requires a matching `of_node_put()`.

The warning about an “excess put” at line 276 may be a symptom of the leak confusing the static analysis, but the code **is buggy** because the reference counting is demonstrably incorrect – multiple GETs lack corresponding PUTs. According to the mandatory rule “If ANY row has GET=YES and PUT=NO → REAL_BUG”, this qualifies as a real refcounting bug.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The loop leaks device_node references on every `continue` path after `of_find_node_with_property` – no `of_node_put` is called for those nodes, violating the contract that the get wrapper requires a put.
```
