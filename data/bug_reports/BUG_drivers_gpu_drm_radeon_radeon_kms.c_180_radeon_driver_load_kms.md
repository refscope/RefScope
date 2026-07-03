# REAL BUG: drivers/gpu/drm/radeon/radeon_kms.c:180 radeon_driver_load_kms()

**Confidence**: HIGH | **Counter**: `dev->dev->power.usage_count.counter`

## Reasoning

| L148-L170 (both init & modeset success) → L177 | success (r == 0) | YES | YES (L170 only) | ✅ | Unload skipped, single put balances the initial get |

## Full Response

```
[NEED_SOURCE] radeon_driver_unload_kms

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L145 (goto out via radeon_device_init failure) | error (r != 0) | LIKELY NO (init failed, no PM get) | YES (radeon_driver_unload_kms at L174 likely does a put) | ❌ LEAK (excess put) | No PM get in error path; unload drops a reference that was never taken |
| L148-L170 (modeset failure, continues) → L174 | error (r != 0) | YES (get done during init) | YES x2 (pm_runtime_put_autosuspend at L170 **+** unload at L174) | ❌ LEAK (double put) | Modeset failure still runs PX block and later unload, causing two puts for one get |
| L148-L170 (both init & modeset success) → L177 | success (r == 0) | YES | YES (L170 only) | ✅ | Unload skipped, single put balances the initial get |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_put_autosuspend` at L170 is unconditional on the PX path. If `radeon_modeset_init` fails (r != 0), the function reaches L170 and does a put, then later at L174 calls `radeon_driver_unload_kms` which likely does another put, resulting in a double put and an excess PM usage count. Additionally, the `radeon_device_init` failure path calls `radeon_driver_unload_kms` without any prior PM get, also causing an excess put.
```
