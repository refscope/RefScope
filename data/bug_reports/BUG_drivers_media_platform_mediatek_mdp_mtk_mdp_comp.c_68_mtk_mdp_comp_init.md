# REAL BUG: drivers/media/platform/mediatek/mdp/mtk_mdp_comp.c:68 mtk_mdp_comp_init()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

- Per the **FP Checklist (Lesson 1)** and **Pre‑Verdict Checklist**, the inability to point to exact cleanup code means we must assume **NO transfer**.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L53 (goto put_dev) | error (clock get fails) | YES (unless `node` is NULL) | YES (at `put_dev`, L64) | ✅ | Error path explicitly releases the `dev_node` reference. |
| L61 (return 0) | success | YES (unless `node` is NULL) | NO | ❌ | Success path returns without releasing the reference stored in `comp->dev_node`. |

**Details**  
- **GET**: `of_node_get(node)` at L45 is unconditional — it increments the kobject refcount if `node` is non‑NULL.  
- **PUT**: `of_node_put(comp->dev_node)` at L64 only executed on the error path via the `put_dev` label.  
- **Success path** (`return 0` at L61) never calls `of_node_put`.  
- No `IS_ERR`/`NULL` guard on the return value of `of_node_get` — the success path assumes the reference was acquired and does not release it.

**Ownership Transfer Assessment**  
- The reference is stored in the `comp->dev_node` field, a long‑lived structure.  
- **Cleanup code**: No line number or function name can be provided within the current context that would eventually `of_node_put(comp->dev_node)`.  
- Per the **FP Checklist (Lesson 1)** and **Pre‑Verdict Checklist**, the inability to point to exact cleanup code means we must assume **NO transfer**.  

**VERDICT: REAL_BUG**  
**CONFIDENCE: LOW**  

`of_node_get(node)` at L45 increments the reference, but the success return at L61 does not call `of_node_put`. While the pattern suggests the reference is intended to be held for the component’s lifetime and released elsewhere, no concrete cleanup release point is visible in the provided source, making the missing put on the success path a refcount leak according to strict audit rules.
```
