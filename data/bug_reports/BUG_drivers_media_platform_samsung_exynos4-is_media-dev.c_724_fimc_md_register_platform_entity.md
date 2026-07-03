# REAL BUG: drivers/media/platform/samsung/exynos4-is/media-dev.c:724 fimc_md_register_platform_entity()

**Confidence**: LOW | **Counter**: `$->dev.of_node->kobj.kref.refcount.refs.counter`

## Reasoning

| L705 (IDX_CSIS, then L715) | depends on register_csis_entity | UNKNOWN | UNKNOWN | ❓ | Needs `register_csis_entity` source; smatch sees excess put at caller return |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L692 (goto dev_unlock) | error | N/A (register_csis_entity not called) | N/A | ✅ | No of_node get/put involved |
| L696 (drvdata NULL, fallthrough to L715) | success/error | N/A | N/A | ✅ | No register call |
| L705 (IDX_CSIS, then L715) | depends on register_csis_entity | UNKNOWN | UNKNOWN | ❓ | Needs `register_csis_entity` source; smatch sees excess put at caller return |

VERDICT: REAL_BUG
CONFIDENCE: LOW
[NEED_SOURCE] register_csis_entity
Warning indicates an excess `of_node_put` on `dev->of_node` at caller return; without callee source, likely a put-without-get imbalance in the IDX_CSIS path.
```
