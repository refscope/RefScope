# REAL BUG: drivers/block/nbd.c:2446 nbd_genl_reconfigure()

**Confidence**: MEDIUM | **Counter**: `$->config_refs.refs.counter`

## Reasoning

l through to out) | return ret after out | config: YES + nbd_reconnect_socket likely increments config_refs (contract: two refcount_inc) | config: YES (only one nbd_config_put at out) | ❌ LEAK | extra config ref from each successful reconnect is never released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2314 (cap check) | error -EPERM | NO | N/A | ✅ | before any get |
| L2318 (attr missing) | error -EINVAL | NO | N/A | ✅ | |
| L2323 (nbd not found) | error -EINVAL | NO (no config get) | N/A | ✅ | |
| L2328-2332 (backend mismatch, ident present) | error -EINVAL | NO | N/A | ✅ | only index_mutex held, released before return |
| L2334-2338 (backend missing ident) | error -EINVAL | NO | N/A | ✅ | |
| L2340 (refcount_inc_not_zero fail) | error -EINVAL | NO (device ref not obtained) | N/A | ✅ | |
| L2346-2350 (config NULL) | error -EINVAL | config: NO (get failed) | device: YES (nbd_put) | ✅ | |
| L2353 (test_bit fail → out) | goto out | config: YES (from nbd_get_config_unlocked) | config: YES (nbd_config_put at out) | ✅ | out balances both config and device |
| L2358 (size_set error → out) | goto out | config: YES | config: YES (at out) | ✅ | |
| L2378 (socket parse error → out) | goto out | config: YES | config: YES (at out) | ✅ | |
| L2390 (reconnect error, non‑ENOSPC → out) | goto out | config: YES, reconnect may not have incremented config_refs on error | config: YES (at out) | ✅ (likely) | nbd_reconnect_socket error path presumably no extra get |
| L2390 (reconnect error, -ENOSPC → out, ret=0) | goto out | config: YES, reconnect possibly got config_refs (unclear) | config: YES (at out) | ⚠️ possible leak | if -ENOSPC still acquired config ref, the single put at out is insufficient |
| L2390+loop (all reconnects succeed, fall through to out) | return ret after out | config: YES + nbd_reconnect_socket likely increments config_refs (contract: two refcount_inc) | config: YES (only one nbd_config_put at out) | ❌ LEAK | extra config ref from each successful reconnect is never released |

[NEED_SOURCE] nbd_reconnect_socket

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

After successful nbd_reconnect_socket calls, config_refs is incremented (contract shows two refcount_inc, one likely for config_refs) but the function only performs a single nbd_config_put at the `out` label, leaving the extra reference(s) unreleased. The inconsistent counter on config_refs stems from this missing put.
```
