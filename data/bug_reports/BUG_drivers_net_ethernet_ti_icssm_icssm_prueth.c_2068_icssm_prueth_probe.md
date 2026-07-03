# REAL BUG: drivers/net/ethernet/ti/icssm/icssm_prueth.c:2068 icssm_prueth_probe()

**Confidence**: HIGH | **Counter**: `$->dev.kobj.kref.refcount.refs.counter`

## Reasoning

The two early error paths (pru0 get failure and pru1 get failure) go to labels that do not contain the necessary `pru_rproc_put`, leading to a permanent leak of the acquired kref.

## Full Response

```
We need to audit the refcount handling for `pru_rproc_get` in the probe function. The contract states `pru_rproc_get` is unconditional: it always increments the kref. The error paths after calling it must therefore call `pru_rproc_put`.  
The function has two early error paths after obtaining pru0 or pru1 that skip the corresponding release, causing a leak.

## Path Table

| Path (label) | Return type | GET pru0? | GET pru1? | PUT pru0? | PUT pru1? | Balanced? | Notes |
|---------------|-------------|-----------|-----------|-----------|-----------|-----------|--------|
| pru0 get error → `goto put_eth` | error (early) | YES (uncond) | NO | NO | NO | ❌ leak pru0 | `put_eth` only does `of_node_put`; no `pru_rproc_put` |
| pru1 get error → `goto put_pru0` | error (early) | YES (if eth0_node) | YES (uncond) | YES (if eth0_node) | NO | ❌ leak pru1 | `put_pru0` puts pru0 only; pru1 acquired but never put |
| `pruss_get` error → `goto put_pru1` | error | YES | YES | YES | YES | ✅ | falls through to `put_pru1` and `put_pru0` |
| memory request error → `goto put_mem` | error | YES | YES | YES | YES | ✅ | falls through to `put_pru1`/`put_pru0` |
| gen_pool_get/alloc error → `goto put_mem` | error | YES | YES | YES | YES | ✅ | same |
| netdev_init eth0 error → `goto free_pool` | error | YES | YES | YES | YES | ✅ | falls through to `put_mem` → `put_pru1`/`put_pru0` |
| netdev_init eth1 error → `goto netdev_exit` | error | YES | YES | YES | YES | ✅ | same |
| `icss_iep_get` error → `goto netdev_exit` | error | YES | YES | YES | YES | ✅ | same |
| register_netdev eth0 error → `goto iep_put` | error | YES | YES | YES | YES | ✅ | falls through to `netdev_exit` → … → `put_pru1`/`put_pru0` |
| register_netdev eth1 error → `goto netdev_unregister` | error | YES | YES | YES | YES | ✅ | same |
| notifiers error → `goto netdev_unregister` | error | YES | YES | YES | YES | ✅ | same |
| success `return 0` | success | YES | YES (if eth1) | NO | NO | ✅ (held) | reference held for device lifetime; removed in `icssm_prueth_remove()` |

The two early error paths (pru0 get failure and pru1 get failure) go to labels that do not contain the necessary `pru_rproc_put`, leading to a permanent leak of the acquired kref.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unconditional `pru_rproc_get` in probe increments refcount; early error paths `goto put_eth` / `goto put_pru0` skip the matching `pru_rproc_put`, causing leaks.
```
