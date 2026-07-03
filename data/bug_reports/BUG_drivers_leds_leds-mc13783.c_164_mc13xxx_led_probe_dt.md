# REAL BUG: drivers/leds/leds-mc13783.c:164 mc13xxx_led_probe_dt()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L167 | success         | YES (every child)                      | NO                                          | ❌ LEAK    | same as above – child refs never released |

## Full Response

```
```
| Line | Return Type | GET Done?                               | PUT Done?                                   | Balanced? | Notes |
|------|-------------|-----------------------------------------|---------------------------------------------|-----------|-------|
| L119 | error (ENOMEM) | NO                               | N/A                                         | ✅        | pdata allocation fails – no node obtained |
| L126 | error (ENODATA) | YES (parent via `of_get_child_by_name`) | YES (auto via `__free(device_node)`)        | ✅        | parent auto-put on scope exit; no children yet |
| L132 | error (ret)     | YES (parent)                           | YES (auto)                                  | ✅        | parent auto-put |
| L138 | error (ENOMEM)  | YES (parent)                           | YES (auto)                                  | ✅        | parent auto-put |
| L164 | error (ENODATA) | YES (every child via `for_each_available_child_of_node`) | NO  | ❌ LEAK    | all child node references leaked; no `of_node_put(child)` |
| L167 | success         | YES (every child)                      | NO                                          | ❌ LEAK    | same as above – child refs never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`for_each_available_child_of_node` acquires reference on each child, but the loop never calls `of_node_put(child)`, leaking all child nodes on both error (L164) and success (L167) returns. The automatic cleanup (`__free`) applies only to `parent`, not to `child`.
```
