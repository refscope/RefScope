# REAL BUG: drivers/mtd/nand/raw/cadence-nand-controller.c:3116 cadence_nand_chips_init()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

hips_cleanup` may call `of_node_put`, double-putting `nand_np`. The scoped cleanup then does an excess put because the refcount is already 0. |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3103 | error (-EINVAL) | NO (before loop) | N/A | ✅ | No child iteration |
| L3111 | error (ret) | YES (of_get_next_child) | YES (scoped cleanup) but chips_cleanup likely puts → excess | ❌ EXCESS PUT | `cadence_nand_chips_cleanup` may call `of_node_put`, double-putting `nand_np`. The scoped cleanup then does an excess put because the refcount is already 0. |
| L3115 | success (0) | YES (for each child, balanced) | YES (scoped cleanup) | ✅ | loop finishes normally, scoped cleanup releases each child correctly |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

`for_each_child_of_node_scoped` unconditionally gets a reference on `nand_np`. On the error path (L3111), `cadence_nand_chips_cleanup` is called before returning; if it internally calls `of_node_put` on the same child node or its stored of_node pointer without an extra `of_node_get`, the refcount will be dropped to zero, and the subsequent scoped cleanup (which runs at function exit) will produce an excess put as warned.
```
```
