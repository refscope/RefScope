# REAL BUG: drivers/regulator/core.c:6261 regulator_register()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| Success return rdev | success | YES | deferred | ✅ | of_node ref held for device lifetime, released in regulator_unregister |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| cfg == NULL return | error return | NO | N/A | ✅ | |
| goto rinse (descriptor NULL) | error | NO | N/A | ✅ | |
| goto rinse (name/ops NULL) | error | NO | N/A | ✅ | |
| goto rinse (type invalid) | error | NO | N/A | ✅ | |
| goto rinse (get_voltage_sel w/o list_voltage) | error | NO | N/A | ✅ | |
| goto rinse (set_voltage_sel w/o list_voltage) | error | NO | N/A | ✅ | |
| goto rinse (kzalloc_obj NULL) | error | NO | N/A | ✅ | |
| goto clean (config == NULL) | error via clean->rinse | NO | N/A | ✅ | |
| goto clean (init_data == -EPROBE_DEFER) | error via clean->rinse | NO | N/A | ✅ | before of_node_get |
| After of_node_get, goto wash (constraints NULL) | error (wash->clean->rinse) | YES | NO | ❌ LEAK | of_node_get ref not dropped |
| After of_node_get, goto wash (init_cb failure) | error (wash->clean->rinse) | YES | NO | ❌ LEAK | |
| After of_node_get, goto wash (ena_gpio request failure) | error (wash->clean->rinse) | YES | NO | ❌ LEAK | |
| After of_node_get, goto wash (set_machine_constraints failure, ret != -EPROBE_DEFER) | error (wash->clean->rinse) | YES | NO | ❌ LEAK | |
| After of_node_get, goto wash (regulator_init_coupling failure) | error (wash->clean->rinse) | YES | NO | ❌ LEAK | |
| After of_node_get, goto unset_supplies (add consumer supplies failure) | error (unset_supplies->wash->clean->rinse) | YES | NO | ❌ LEAK | |
| After of_node_get, goto unset_supplies (device_add failure) | error (unset_supplies->wash->clean->rinse) | YES | NO | ❌ LEAK | |
| After of_node_get, goto del_cdev_and_bdev (bdev device_add failure) | error (del_cdev_and_bdev->unset_supplies->wash->clean->rinse) | YES | NO | ❌ LEAK | |
| Success return rdev | success | YES | deferred | ✅ | of_node ref held for device lifetime, released in regulator_unregister |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get` inside `if (!init_data)` acquires a reference; every error path after that (`goto wash`, `goto unset_supplies`, `goto del_cdev_and_bdev`) lacks `of_node_put`, causing a leak.
```
