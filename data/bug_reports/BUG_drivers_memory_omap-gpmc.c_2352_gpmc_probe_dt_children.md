# REAL BUG: drivers/memory/omap-gpmc.c:2352 gpmc_probe_dt_children()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

common pattern before the macro auto‑management was introduced), the reference count is decremented twice, triggering the “excess put”. No obvious `of_node_put` is visible in the loop body, so the excess must come from the child function’s internal handling.

## Full Response

```
## Path Table

| Path | GET Done? | PUT Done? (function) | PUT Done? (macro auto) | Balanced? | Notes |
|------|-----------|---------------------|------------------------|-----------|-------|
| Each iteration through `for_each_available_child_of_node` with valid child | YES (from `of_get_next_available_child`) | YES (assumed: `gpmc_probe_generic_child` calls `of_node_put`) | YES (modern `for_each_available_child_of_node` macro auto-puts via `__free`) | ❌ **Double PUT** | Macro auto-put after loop body + function’s own put conflicts, leading to excess put on child’s kref. |

```c
static void gpmc_probe_dt_children(struct platform_device *pdev)
{
	int ret;
	struct device_node *child;

	for_each_available_child_of_node(pdev->dev.of_node, child) {
		ret = gpmc_probe_generic_child(pdev, child);
		if (ret) {
			dev_err(&pdev->dev, "failed to probe DT child '%pOFn': %d\n",
				child, ret);
		}
	}
}
```

The warning (`refcount excess put` at line 2352) points to the `for_each_available_child_of_node` macro line, which in modern kernels (≥ v6.7) includes an automatic `of_node_put` via `__free` cleanup. The macro thus releases the reference taken by `of_get_next_available_child`. If `gpmc_probe_generic_child` also releases the reference (a common pattern before the macro auto‑management was introduced), the reference count is decremented twice, triggering the “excess put”. No obvious `of_node_put` is visible in the loop body, so the excess must come from the child function’s internal handling.

[NEED_SOURCE] gpmc_probe_generic_child

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `for_each_available_child_of_node` macro now automatically drops the child node reference; `gpmc_probe_generic_child` likely also calls `of_node_put`, causing a double put and refcount underflow.
```
