# REAL BUG: drivers/irqchip/irq-stm32mp-exti.c:698 stm32mp_exti_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L698 | success     | YES | NO   | ❌ LEAK | successful probe, leaks of_irq_find_parent ref |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L633 | error       | NO (before get) | N/A  | ✅ | devm_kzalloc fail |
| L642 | error       | NO (before get) | N/A  | ✅ | -EPROBE_DEFER before get |
| L648 | error       | NO (before get) | N/A  | ✅ | hwlock request fail |
| L653 | error       | NO (before get) | N/A  | ✅ | hwspinlock get fail |
| L660 | error       | NO (before get) | N/A  | ✅ | no match data |
| L668 | error       | NO (before get) | N/A  | ✅ | chips_data alloc fail |
| L672 | error       | NO (before get) | N/A  | ✅ | ioremap fail |
| L682 | error       | ❓ (GET maybe done if parent node non-NULL) | NO | ❌ POTENTIAL LEAK | irq_find_host returned NULL; of_irq_find_parent may have incremented ref if non-NULL |
| L689 | error       | YES | NO   | ❌ LEAK | irq_domain_create_hierarchy fails, leaks of_irq_find_parent ref |
| L694 | error       | YES | NO   | ❌ LEAK | devm_add_action_or_reset fails, leaks of_irq_find_parent ref |
| L698 | success     | YES | NO   | ❌ LEAK | successful probe, leaks of_irq_find_parent ref |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_irq_find_parent(np)` at line 679 acquires a reference on the returned device node that is never released by `of_node_put`, leaking it on all paths after that call where `parent_domain` is non-NULL (including the success return at line 698 and error paths at 689, 694).
```
