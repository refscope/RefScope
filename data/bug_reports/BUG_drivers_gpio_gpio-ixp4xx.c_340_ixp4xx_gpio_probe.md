# REAL BUG: drivers/gpio/gpio-ixp4xx.c:340 ixp4xx_gpio_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L345 | success (0) | YES | NO | ❌ LEAK | probe success, irq_parent reference never released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L214 | error (-ENOMEM) | NO (before get) | N/A | ✅ | |
| L219 | error (PTR_ERR) | NO (before get) | N/A | ✅ | |
| L224 | error (-ENODEV) | NO (irq_parent == NULL) | N/A | ✅ | of_irq_find_parent returned NULL |
| L230 | error (-ENODEV) | YES | NO | ❌ LEAK | irq_find_host failed, missing of_node_put(irq_parent) |
| L275 | error (ret) | YES | NO | ❌ LEAK | gpio_generic_chip_init fail path, missing put |
| L340 | error (ret) | YES | NO | ❌ LEAK | devm_gpiochip_add_data fail path, missing put |
| L345 | success (0) | YES | NO | ❌ LEAK | probe success, irq_parent reference never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_irq_find_parent` returns a `struct device_node*` with a reference. No `of_node_put` is called on any path after a successful non-NULL return. All error and success paths after `irq_parent` becomes valid leak it.
```
