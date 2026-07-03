# REAL BUG: drivers/regulator/core.c:2374 regulator_resolve_supply()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2320 | out: return ret (from do_final_setup false path after put) | YES | YES | ✅ | Already released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2173 | return 0 (no supply name) | NO | N/A | ✅ | Before any get |
| L2178 | return 0 (supply already resolved) | NO | N/A | ✅ | Before any get |
| L2195 | goto out (IS_ERR(r), defer) | NO | N/A | ✅ | r is ERR, no ref |
| L2203 | goto out (IS_ERR(r), !have_full_constraints) | NO | N/A | ✅ | r is ERR, no ref |
| L2208 | goto out (IS_ERR(r), have_full_constraints but dummy NULL) | NO | N/A | ✅ | r is NULL, no ref |
| L2218 | goto out (r == rdev, !have_full_constraints) | YES (lookup ref) | NO | ❌ LEAK | Missing put_device for original r |
| L2232 | goto out (parent not bound) | YES | YES | ✅ | put_device before goto |
| L2240 | goto out (recursive resolve fails) | YES | YES | ✅ | put_device before goto |
| L2253 | goto out (lock_two, rdev->supply exists, done true) | YES | YES | ✅ | put_device before goto |
| L2260 | goto out (lock_two, rdev->supply exists, done false; already put) | YES | YES | ✅ | put_device done earlier |
| L2269 | goto out (lock_two, set_supply fails) | YES | YES | ✅ | put_device before goto |
| L2278 | goto unset_supply (lock_two, set_supply ok, event_forwarding fails) | YES | NO | ❌ LEAK | unset_supply has no put_device |
| L2285–L2310 | (lock_two, set_supply+event_forwarding ok, do_final_setup=true) any exit to out or unset_supply from constraints_pending block | YES | NO | ❌ LEAK | No put_device on any of:
- `!rdev->supply` → goto out
- `set_machine_constraints` fail & supply changed → goto out
- `set_machine_constraints` fail else → goto unset_supply
- success → out via link_and_create_debugfs
All leak the reference held from get_device / lookup. |
| L2320 | out: return ret (from do_final_setup false path after put) | YES | YES | ✅ | Already released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After successful `set_supply()` and `register_regulator_event_forwarding()`, the function does not call `put_device(&r->dev)` on any of the subsequent success or error paths (constraints_pending block, final out). The same bug applies to the `goto unset_supply` path on event forwarding failure. The reference obtained via `get_device()` or the lookup is never released, causing a refcount leak on the supply device.
```
