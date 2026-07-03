# REAL BUG: drivers/media/platform/samsung/exynos4-is/media-dev.c:493 fimc_md_parse_port_node()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L492 | success return 0 | YES (final non-NULL ep ref held; loop cleanup runs) | YES (loop cleanup puts final ep) | YES (same) | NO (excess put) | Same double put after callee already released reference. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? (loop) | PUT by callee? | Balanced? | Notes |
|------|-------------|-----------|-----------------|----------------|-----------|-------|
| L489 | error return (ret < 0) | YES (ep ref from of_get_next_child via for_each_child_of_node_scoped) | YES (loop's scoped cleanup does of_node_put(ep)) | YES (fimc_md_parse_one_endpoint calls of_node_put on ep) | NO (excess put, underflow) | Loop’s automatic put after callee’s put causes double put. |
| L492 | success return 0 | YES (final non-NULL ep ref held; loop cleanup runs) | YES (loop cleanup puts final ep) | YES (same) | NO (excess put) | Same double put after callee already released reference. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`for_each_child_of_node_scoped` correctly manages the endpoint node refcount, but `fimc_md_parse_one_endpoint` contains an `of_node_put` (as confirmed by contract) on the same node, leading to a double put and underflow at loop cleanup.
```
