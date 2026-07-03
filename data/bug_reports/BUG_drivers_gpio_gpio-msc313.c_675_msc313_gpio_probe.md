# REAL BUG: drivers/gpio/gpio-msc313.c:675 msc313_gpio_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

4. goto out? No goto labels; direct returns after the get.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L613 | { | N/A | N/A | N/A | function entry |
| L624 | return -EINVAL | NO (before get) | N/A  | ✅ | of_irq_find_parent not called yet |
| L628 | return -ENODEV | NO (get failed: parent_node==NULL) | N/A  | ✅ | of_irq_find_parent returned NULL, no ref held |
| L632 | return -ENODEV | YES (parent_node != NULL) | NO   | ❌ LEAK | of_node_put never called |
| L636 | return -ENOMEM | YES | NO   | ❌ LEAK | no put |
| L642 | return -ENOMEM | YES | NO   | ❌ LEAK | no put |
| L646 | return PTR_ERR(gpio->base) | YES | NO   | ❌ LEAK | no put |
| L652 | return -ENOMEM | YES | NO   | ❌ LEAK | no put |
| L675 | return devm_gpiochip_add_data(...) | YES | NO   | ❌ LEAK | no of_node_put anywhere in function |

**Pre-Verdict Checklist**:
1. "Held for device lifetime"? Not documented; no devm cleanup for this of node handle.
2. "Ownership transferred"? No; parent_node is not stored in a long-lived structure; no documented cleanup.
3. Unconditional GET? After of_irq_find_parent returns non-NULL, a reference is held (contract confirms it's a get). All subsequent paths must call of_node_put.
4. goto out? No goto labels; direct returns after the get.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_irq_find_parent` acquires a reference that must be released via `of_node_put`, but the function returns without releasing it on every path where `parent_node` is non-NULL, including the error path at L632 and the success path at L675.
```
