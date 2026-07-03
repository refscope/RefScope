# REAL BUG: drivers/irqchip/irqchip.c:58 platform_irqchip_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L58 (par_np == np) | return irq_probe(…, NULL) | YES (initial ref on np) | NO (par_np set to NULL; cleanup calls of_node_put(NULL)) | ❌ LEAK | `par_np = NULL;` discards the reference without of_node_put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L39 | return -EINVAL | YES (if par_np != NULL) | YES (via `__free(device_node)` cleanup) | ✅ | par_np not yet nulled |
| L52 | return -EPROBE_DEFER | YES (par_np non‑NULL) | YES (cleanup) | ✅ | only reachable when par_np != NULL |
| L58 (par_np != np) | return irq_probe(…, par_np) | YES (par_np holds ref) | YES (cleanup after irq_probe returns) | ✅ | |
| L58 (par_np == np) | return irq_probe(…, NULL) | YES (initial ref on np) | NO (par_np set to NULL; cleanup calls of_node_put(NULL)) | ❌ LEAK | `par_np = NULL;` discards the reference without of_node_put |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_irq_find_parent` returns a reference (unconditional on success). When `par_np == np`, the code sets `par_np = NULL` without calling `of_node_put`, leaking the reference. The `__free(device_node)` cleanup only releases if the pointer is non‑NULL, so no put occurs on the final return.
```
