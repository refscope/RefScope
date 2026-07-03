# REAL BUG: sound/soc/qcom/common.c:1577 of_get_available_child_count()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

e without a matching get, or double-puts on loop exit). If the macro were a plain get‑only iterator, the warning would be a refcount leak, not an excess put. The presence of “excess put” therefore points to a bug in the macro’s reference counting logic or a mismatch with the caller’s expectations.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1577 | normal return | ?         | ?         | ?         | Inside loop `for_each_available_child_of_node`; need macro source to determine get/put semantics |

[NEED_SOURCE] for_each_available_child_of_node
[NEED_SOURCE] of_get_next_available_child

Without the macro definition, the get/put balance of the loop cannot be verified. The warning is “refcount excess put”, which implies an extra `of_node_put` is called somewhere—most likely inside the loop expansion. Since the body only increments a counter and does not call any `of_node_put`, an excess put would originate from the macro itself, suggesting a mismatch (e.g., the macro puts a node without a matching get, or double-puts on loop exit). If the macro were a plain get‑only iterator, the warning would be a refcount leak, not an excess put. The presence of “excess put” therefore points to a bug in the macro’s reference counting logic or a mismatch with the caller’s expectations.

VERDICT: REAL_BUG
CONFIDENCE: LOW
Exact macro expansion required; based on warning type, an extra `of_node_put` inside the loop is likely, causing an unbalanced put when no matching get was performed.
```
