# REAL BUG: drivers/platform/arm64/huawei-gaokun-ec.c:708 gaokun_aux_init()

**Confidence**: HIGH | **Counter**: `$->of_node->kobj.kref.refcount.refs.counter`

## Reasoning

| L704 | `return ret` (add failure) | YES | NO | ❌ LEAK | `of_node_put` missing; `adev` also leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L684 | `return -ENOMEM` | NO (before `device_set_of_node_from_dev`) | N/A | ✅ | No get yet |
| L698 | `return ret` (init failure) | YES | YES (manual `of_node_put` at L696) | ✅ | Proper cleanup |
| L704 | `return ret` (add failure) | YES | NO | ❌ LEAK | `of_node_put` missing; `adev` also leaked |
| L707 | success (`devm_add_action_or_reset`) | YES | YES (via release later) | ✅ | Ownership transferred to devm |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`device_set_of_node_from_dev()` is unconditional; error path after `auxiliary_device_add()` failure (L704) skips `of_node_put` and `kfree`, leaking the kref reference and the device memory.
```
