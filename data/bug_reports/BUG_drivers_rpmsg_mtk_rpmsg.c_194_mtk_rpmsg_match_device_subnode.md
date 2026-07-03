# REAL BUG: drivers/rpmsg/mtk_rpmsg.c:194 mtk_rpmsg_match_device_subnode()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

function would only leak refs on the non‑returned children, which is a different class of imbalance (refcount leak) and not the “excess put” reported. Therefore, the most likely scenario given the warning is that the macro does auto‑put, making the `return child` path a real double‑release bug.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L193 `return child;` | success (match found) | **YES** – `of_get_next_available_child()` (unconditional) | **UNCERTAIN** – depends on `for_each_available_child_of_node` macro: if it includes `__free(of_node_put)` then **PUT=YES** (auto‑cleanup), otherwise **PUT=NO** | **UNBALANCED if macro auto‑puts** → excess put (double‑release when caller later calls `of_node_put(child)`) | If macro does **not** auto‑put, this path returns a valid reference to the caller – balanced externally but no internal put. |
| L194 `return NULL;` | no match found, loop exhausted | **YES** – last `child` obtained by `of_get_next_available_child()` before loop termination | **UNCERTAIN** – if macro auto‑puts then **PUT=YES** (cleanup puts the last child, so ref is released). If not, **PUT=NO** (leak of last child’s ref, but leak ≠ excess put) | **No excess‑put risk** on this path: auto‑put on NULL is safe; leak is a different issue. | The warning is at this line, but the actual excess‑put likely originates from the previous path (return child) if internal put occurs. |

[NEED_SOURCE] for_each_available_child_of_node  
[NEED_SOURCE] of_get_next_available_child

**Rationale:**  
The “excess put” warning indicates a reference was decremented without a matching get. In `mtk_rpmsg_match_device_subnode()`, no explicit `of_node_put()` is present. The only possible source of an unexpected put is an automatic cleanup introduced by modern iterator macros (e.g., `__free(of_node_put)`). When `return child;` is executed, the `child` variable goes out of scope and the cleanup calls `of_node_put(child)`, releasing the reference that `of_get_next_available_child()` had obtained. The caller, expecting the function to return a node with a held reference, later calls `of_node_put()` on the same node, causing a double‑decrement — an **excess put**.  
If the macro does **not** include a put, the function would only leak refs on the non‑returned children, which is a different class of imbalance (refcount leak) and not the “excess put” reported. Therefore, the most likely scenario given the warning is that the macro does auto‑put, making the `return child` path a real double‑release bug.

## VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
*Confidence is medium until the source of `for_each_available_child_of_node` is confirmed; if the macro includes an auto‑put (modern kernel), the warning is a true double‑release. If not, the warning may be mis‑categorized but the function would still leak child refs.*
```
