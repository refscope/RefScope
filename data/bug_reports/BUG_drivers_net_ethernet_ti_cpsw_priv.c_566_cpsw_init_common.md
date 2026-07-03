# REAL BUG: drivers/net/ethernet/ti/cpsw_priv.c:566 cpsw_init_common()

**Confidence**: HIGH | **Counter**: `cpts_node->kobj.kref.refcount.refs.counter`

## Reasoning

| L566 | success/error (ret) | **YES** (if "cpts" child found, via `of_get_child_by_name`) / **NO** (if child not found, uses parent `cpsw->dev->of_node` without get) | YES (unconditional `of_node_put`) | ❌ on child‑not‑found path | parent `of_node` put without matching get → excess put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L497 | error (-ENODEV) | N/A (before cpts_node) | N/A | ✅ | return before cpts_node assignment |
| L507 | error (PTR_ERR) | N/A (before cpts_node) | N/A | ✅ | loop early return |
| L517 | error (PTR_ERR) | N/A (before cpts_node) | N/A | ✅ | cpsw_ale_create failure |
| L540 | error (-ENOMEM) | N/A (before cpts_node) | N/A | ✅ | dma creation failure |
| L566 | success/error (ret) | **YES** (if "cpts" child found, via `of_get_child_by_name`) / **NO** (if child not found, uses parent `cpsw->dev->of_node` without get) | YES (unconditional `of_node_put`) | ❌ on child‑not‑found path | parent `of_node` put without matching get → excess put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `of_get_child_by_name` returns NULL, `cpts_node` is assigned `cpsw->dev->of_node` without taking a reference, yet `of_node_put(cpts_node)` is called unconditionally at the end, causing a refcount excess put on the parent device node.
```
