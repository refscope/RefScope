# REAL BUG: drivers/infiniband/hw/mlx4/sysfs.c:352 add_port_entries()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L330 | success return 0 | cur_port ref=4 (all parents) | no PUT needed (lifetime) | ✅ | objects kept for active use |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L235 | goto err (query fail) | NO (no kobject_get) | N/A | ✅ | |
| L248 | goto err (kzalloc fail) | NO | N/A | ✅ | |
| L258 | goto kobj_create_err (cur_port fail) | GET on device->ports_parent, but cur_port NOT created | PUT device->ports_parent at kobj_create_err; no cur_port PUT | ✅ | explicit parent get balanced |
| L265 | goto err_admin_guids (admin_alias fail) | GET on device->ports_parent; cur_port created (ref=1) | PUT device->ports_parent ONCE; cur_port PUT TWICE via cascade | ❌ OVER-RELEASE | cur_port refcount underflow (put twice, only one ref held) |
| L275 | goto err_admin_alias_parent (admin loop fail) | cur_port ref=2 (initial + admin_alias parent get) | admin_alias PUT (releases cur_port once) + cur_port explicit PUT x2; total cur_port PUT 3 | ❌ OVER-RELEASE | cur_port over-released |
| L286 | goto err_gids (gids_parent fail) | cur_port ref=2 (admin_alias parent get) | cur_port explicit PUT x3 + admin_alias PUT (releases cur_port once); total cur_port PUT 4 | ❌ OVER-RELEASE | |
| L297 | goto err_gids_parent (gids loop fail) | cur_port ref=3 (admin+gids parent gets) | gids_parent PUT (releases cur_port) + cur_port explicit PUT x3 + admin_alias PUT (releases cur_port); total cur_port PUT 5 | ❌ OVER-RELEASE | |
| L307 | goto err_pkeys (pkeys_parent fail) | cur_port ref=3 (admin+gids) | cur_port explicit PUT x1 + gids_parent PUT (cur_port) + cur_port PUT x1 + admin_alias PUT (cur_port) + cur_port PUT x2; total 6 | ❌ OVER-RELEASE | |
| L318 | goto err_pkeys_parent (pkeys loop fail) | cur_port ref=4 (admin+gids+pkeys) | pkeys_parent PUT (cur_port) + cur_port PUT x1 + gids_parent PUT (cur_port) + cur_port PUT x1 + admin_alias PUT (cur_port) + cur_port PUT x2; total 7 | ❌ OVER-RELEASE | |
| L326 | goto err_mcgs (mcgs_parent fail) | cur_port ref=4 (admin+gids+pkeys) | cur_port PUT (err_mcgs) + pkeys_parent PUT (cur_port) + cur_port PUT (err_pkeys) + gids_parent PUT (cur_port) + cur_port PUT (err_gids) + admin_alias PUT (cur_port) + cur_port PUT x2; total 8 | ❌ OVER-RELEASE | |
| L330 | success return 0 | cur_port ref=4 (all parents) | no PUT needed (lifetime) | ✅ | objects kept for active use |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error cleanup cascade incorrectly puts `port->cur_port` multiple times on every error path after its creation, leading to over-release and use-after-free or refcount underflow.
```
