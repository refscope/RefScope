# REAL BUG: drivers/of/overlay.c:847 init_overlay_changeset()

**Confidence**: HIGH | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

At L847, `of_node_put(node)` drops a reference that had already been transferred to `fragment->overlay`. The function’s comment promises that the caller will call `free_overlay_changeset()` on error, which will again put that stored node, causing an over-release and inconsistent refcounting.

## Full Response

```
| Line (approx) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|--------------|-------------|-----------|-----------|-----------|-------|
| return 0 (~L835) | success | YES (fragment->overlay & fragment->target stored) | NO immediate, but caller’s free_overlay_changeset will release | ✅ | Ownership of refs transferred to changeset for caller cleanup |
| goto err_out after kzalloc_objs fail (~L785) | error (ENOMEM) | NO (no fragment refs stored) | N/A | ✅ | No refs acquired that are not already released |
| goto err_out in second loop (~L805) | error (EINVAL) | YES (overlay_node, node) | YES (manual of_node_put for both) but fragment->overlay still points to overlay_node | ❌ OVER-RELEASE | Caller will later put overlay_node via free_overlay_changeset → double put |
| goto err_out for !cnt (~L830) | error (EINVAL) | YES (fragments from loop stored) | NO immediate; caller cleanup | ✅ | All refs safely stored in changeset |
| goto err_out in symbols error (~L847) | error (EINVAL) | YES (node from of_get_child_by_name) | YES (manual of_node_put(node)) but fragment->overlay still points to node | ❌ OVER-RELEASE | Caller will later put node via free_overlay_changeset → double put |

At L847, `of_node_put(node)` drops a reference that had already been transferred to `fragment->overlay`. The function’s comment promises that the caller will call `free_overlay_changeset()` on error, which will again put that stored node, causing an over-release and inconsistent refcounting.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The manual `of_node_put(node)` at L847 after storing `node` in `fragment->overlay` causes a double‑release when the caller later invokes `free_overlay_changeset()`.
```
