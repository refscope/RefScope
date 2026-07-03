# REAL BUG: sound/soc/renesas/rcar/ssi.c:1140 rsnd_parse_connect_ssi()

**Confidence**: MEDIUM | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

a reference previously acquired by `of_node_get` or equivalent. `rsnd_ssi_of_node` is not listed in the GET contracts; typical driver helpers that return a device‑tree node stored in `priv` do **not** acquire a new reference, making the final `of_node_put` an improper put of a borrowed reference.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1118 | early return (node == NULL) | NO (rsnd_ssi_of_node returned NULL; no ref held) | N/A | ✅ | Safe: NULL pointer, no put needed. |
| L1140 | fall‑through return after loop | **UNCERTAIN** – depends on `rsnd_ssi_of_node` semantics. If it returns a *borrowed* pointer (no refcount increment) → **GET=NO**. If it internally calls `of_get_child_by_name` or similar → **GET=YES**. | YES (`of_node_put(node)`) | ❌ **Excess put** if GET=NO; ✅ balanced if GET=YES. | The warning reports **excess put** on this node's kref, which strongly indicates GET=NO. |

> ⚠️ The contract for `of_node_put` says it releases a reference previously acquired by `of_node_get` or equivalent. `rsnd_ssi_of_node` is not listed in the GET contracts; typical driver helpers that return a device‑tree node stored in `priv` do **not** acquire a new reference, making the final `of_node_put` an improper put of a borrowed reference.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`rsnd_ssi_of_node` likely returns a borrowed pointer without incrementing the refcount; calling `of_node_put` on it is an excess put, consistent with the smatch warning. To confirm, I request `[NEED_SOURCE] rsnd_ssi_of_node`.
```
