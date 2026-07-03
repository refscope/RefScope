# REAL BUG: drivers/regulator/scmi-regulator.c:383 scmi_regulator_probe()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

Given the above, the path table highlights a **leak** on the main node, but the warning is about **excess put**. The available information is insufficient to confirm the bug; the verdict must be UNCLEAR.

## Full Response

```
[NEED_SOURCE] process_scmi_regulator_of_node
[NEED_SOURCE] scmi_regulator_common_init

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 307 | error (-ENODEV) | NO (before any node get) | N/A | ✅ | No refcount operations yet |
| 312 | error (PTR_ERR) | NO (before node get) | N/A | ✅ | |
| 316 | error (0) | NO (before node get) | N/A | ✅ | |
| 322 | error (num_doms) | NO (before node get) | N/A | ✅ | |
| 327 | error (-ENOMEM) | NO (before node get) | N/A | ✅ | |
| 333 | error (-ENOMEM) | NO (before node get) | N/A | ✅ | |
| 343 | (of_node_get call) | – entry point; no return yet | – | – | Acquires ref on handle->dev->of_node |
| 344 | (of_find_node_by_name) | conditional (internal get on np) | – | – | np holds a reference from of_find_node_by_name |
| 349 | return ret (inside loop, -ENOMEM) | YES (of_node_get L343 + np from L344) | NO | ❌ LEAK | omits of_node_put(np) and of_node_put(handle->dev->of_node) |
| 351 | (of_node_put(np)) | – | np ref put | – | np released after loop |
| 383 | success (return 0) | YES (of_node_get L343) | NO | ❌ LEAK | main node ref not released anywhere |

**Notes on the table:**
- The only unconditional `of_node_get` in the provided probe code is at line 343 on `handle->dev->of_node`. No matching `of_node_put` for that node exists anywhere in the visible function, so **the success path (return 0) leaks that reference**.
- The error path inside the loop (line 349) returns without putting `np` (acquired via `of_find_node_by_name`) or the main node ref, so it also leaks both.
- The warning is **excess put**, not leak. The leak of the main node ref cannot cause an excess‑put warning; it would show as a reference never released.
- The excess‑put must therefore involve a node whose refcount is decremented too many times. The most likely candidate is the `child` node passed to `process_scmi_regulator_of_node`. The contract says that function does an **unconditional `of_node_get`** (on something, presumably the child). The loop uses `for_each_child_of_node_scoped` which auto‑puts the child at the end of each iteration (or on early return). If `process_scmi_regulator_of_node` also increments the child’s refcount and stores the pointer without the caller releasing that stored reference, then the auto‑put would be balanced by the stored reference (the net refcount stays correct). However, **if** the function later fails (e.g., -ENOMEM) after having stored the child, the auto‑put still fires (child goes out of scope on the early return), and the stored reference remains, leaving the refcount balanced. That would not be an excess put; it would be a dangling pointer or leak later.
- The warning points to line 383, which likely corresponds to the `return 0;` at the end of the function. No explicit put is visible there, and the auto‑cleanup of `child` is already gone. The existence of an excess‑put warning suggests that *somewhere* within this functi
```
