# REAL BUG: drivers/fsi/fsi-master-gpio.c:865 fsi_master_gpio_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

t a false positive**: The `goto err_free` label is a classical blind spot – it does not contain any refcount cleanup. There is no ownership transfer on those paths because the device is never registered, so `fsi_master_gpio_release` will never be invoked. The reference must be explicitly released.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| after `kzalloc_obj` failure (before of_node_get) | error (-ENOMEM) | NO (GET not yet executed) | N/A | ✅ | |
| any `IS_ERR(gpio)` check leading to `goto err_free` (clock, data, trans, enable, mux) | error (via `goto err_free`) | YES (unconditional of_node_get before all gpio gets) | NO (err_free only does `kfree(master)`) | ❌ LEAK | of_node reference held, never released |
| `device_create_file` failure → `goto err_free` | error (via `goto err_free`) | YES | NO | ❌ LEAK | of_node reference still held, no put |
| `fsi_master_register` failure (returns rc) | error | YES | YES (`put_device` at L865) | ✅ | put_device triggers release, which should of_node_put |
| `return 0` (success) | success | YES | YES (device registered, lifetime managed by framework) | ✅ | |

---
## Audit Reasoning

The function unconditionally performs `of_node_get(dev_of_node(master->dev))` immediately after allocating `master`. This sets `master->master.dev.of_node` and must be matched by an eventual `of_node_put` (or `put_device` that triggers `fsi_master_gpio_release`).

- **Success path (return 0)**: the device is fully registered; release will happen via `fsi_master_gpio_release` when the master is unregistered. No leak.
- **`fsi_master_register` failure**: code explicitly calls `put_device(&master->master.dev)`, which will eventually call the release function and free the node. Balanced.
- **All `gpio` acquisition errors and `device_create_file` failure**: they jump to `err_free` which does only `kfree(master)`. No `put_device` or `of_node_put` is called. The `of_node` reference taken earlier is never released, causing a refcount leak on the kobject backing the device node. ⚠️

**Why this is not a false positive**: The `goto err_free` label is a classical blind spot – it does not contain any refcount cleanup. There is no ownership transfer on those paths because the device is never registered, so `fsi_master_gpio_release` will never be invoked. The reference must be explicitly released.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_node_get` is taken early; all `goto err_free` error paths before `fsi_master_register` success leak the reference because `err_free` only frees memory without an `of_node_put` or `put_device`.
```
