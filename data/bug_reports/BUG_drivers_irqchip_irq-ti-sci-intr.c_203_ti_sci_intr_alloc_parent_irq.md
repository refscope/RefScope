# REAL BUG: drivers/irqchip/irq-ti-sci-intr.c:203 ti_sci_intr_alloc_parent_irq()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L189 | success (return out_irq)     | YES       | NO        | ❌ LEAK    | success path never calls of_node_put                                  |

## Full Response

```
```
| Line | Return Type          | GET Done? | PUT Done? | Balanced? | Notes                                                                 |
|------|----------------------|-----------|-----------|-----------|-----------------------------------------------------------------------|
| L154 | error (return -EINVAL) | NO (before get) | N/A       | ✅         | of_irq_find_parent not yet called                                     |
| L158 | goto err_irqs (p_hwirq < 0) | NO (before get) | N/A       | ✅         | noch nicht gesourced                                                  |
| L183 | goto err_irqs (irq_alloc fails) | YES       | NO        | ❌ LEAK    | parent_node held, err_irqs label has no of_node_put                   |
| L187 | goto err_msg (set_irq fails)  | YES       | NO        | ❌ LEAK    | err_msg→err_irqs still no put                                         |
| L189 | success (return out_irq)     | YES       | NO        | ❌ LEAK    | success path never calls of_node_put                                  |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
of_irq_find_parent() at L160 acquires a reference on parent_node, but no of_node_put() exists on any subsequent path (error or success).
```
```
