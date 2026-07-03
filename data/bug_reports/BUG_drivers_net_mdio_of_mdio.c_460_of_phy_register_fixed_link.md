# REAL BUG: drivers/net/mdio/of_mdio.c:460 of_phy_register_fixed_link()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

er(&status, np)`. `fixed_phy_register` returns `struct phy_device *` with a held reference on success (contract: `conditional_on_path`, internal `of_node_get`/`phy_device_free`). The returned pointer is discarded by `PTR_ERR_OR_ZERO()`, so the phy_device kref is never released on the success path.

## Full Response

```
## Path Table

| Path Description (approx line)                       | Return Type          | GET Done? (fixed_phy_register success) | PUT Done? | Balanced? | Notes                                                                                      |
|-------------------------------------------------------|----------------------|----------------------------------------|-----------|-----------|--------------------------------------------------------------------------------------------|
| managed + in-band, goto register_phy (L416 → L460)    | success/error        | YES (if success, phy_device ref taken) | NO        | ❌ LEAK   | discards phy_device pointer; no put on success                                             |
| new binding success, of_node_put then goto register_phy (L430 → L460) | success/error | YES (if success)                       | NO        | ❌ LEAK   | fixed_link_node ref already released; phy_device ref not released on success              |
| old binding success, goto register_phy (L445 → L460)  | success/error        | YES (if success)                       | NO        | ❌ LEAK   | same as above                                                                              |
| new binding error (L428: return -EINVAL)              | error (-EINVAL)      | NO (no fixed_phy_register call)        | N/A       | ✅         | fixed_link_node ref properly released with of_node_put                                      |
| final return -ENODEV (L448)                           | error (-ENODEV)      | NO                                     | N/A       | ✅         | no get, no leak                                                                            |

**Key:** register_phy label at L460 calls `fixed_phy_register(&status, np)`. `fixed_phy_register` returns `struct phy_device *` with a held reference on success (contract: `conditional_on_path`, internal `of_node_get`/`phy_device_free`). The returned pointer is discarded by `PTR_ERR_OR_ZERO()`, so the phy_device kref is never released on the success path.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`fixed_phy_register` returns a held reference that is always leaked when the function succeeds, because `PTR_ERR_OR_ZERO` discards the pointer and no `put_device`/`phy_device_free` is called. All three `register_phy` paths exhibit the leak.
```
