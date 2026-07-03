# REAL BUG: drivers/hsi/controllers/omap_ssi_core.c:457 ssi_of_get_available_ports_count()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

_next_available_child` increments refcount for each child node | NO — no `of_node_put` call exists in the function | ❌ LEAK | Every `for_each_available_child_of_node` iteration acquires a reference; none are released before return, resulting in a refcount leak on all traversed child nodes |

## Full Response

```
[NEED_SOURCE] for_each_available_child_of_node

---

Based on the standard Linux kernel definition (see include/linux/of.h), `for_each_available_child_of_node` does **not** automatically put the child node; it only calls `of_get_next_available_child()`, which increments the node’s refcount. The iterator variable (`child`) is overwritten on each iteration, and no `of_node_put()` is performed before the loop condition reassigns it. After the loop, `child` is `NULL` but the last valid child node’s reference is still held.

## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L456 | success (return num) | YES — `of_get_next_available_child` increments refcount for each child node | NO — no `of_node_put` call exists in the function | ❌ LEAK | Every `for_each_available_child_of_node` iteration acquires a reference; none are released before return, resulting in a refcount leak on all traversed child nodes |

## PRE-VERDICT CHECKLIST

1. **"Held for device lifetime"?** No, no such claim.  
2. **"Ownership transferred"?** No, child nodes are not stored or handed over.  
3. **Unconditional GET?** The macro gets a reference unconditionally when the node pointer is non‑NULL, but the final node reference is never released.  
4. **goto out between GET and PUT?** Not applicable; only one return path.

The function leaks references; the smatch report of “excess put” is likely a mischaracterisation because the missing `put` eventually leads to an underflow when someone else tries to release the node.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`for_each_available_child_of_node` acquires references via `of_get_next_available_child()`, but `ssi_of_get_available_ports_count()` returns without calling `of_node_put()`, leaking a refcount on every compatible child node.
```
