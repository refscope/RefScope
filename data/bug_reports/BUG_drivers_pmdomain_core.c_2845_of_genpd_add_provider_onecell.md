# REAL BUG: drivers/pmdomain/core.c:2845 of_genpd_add_provider_onecell()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2844 | return 0 (success) | YES (all) | NO (intentional) | ✅ | reference held for device lifetime |

## Full Response

```
| Line | Return Type | GET Done? (device_add) | PUT Done? (put_device) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L2757 | early return -EINVAL | NO | N/A | ✅ | before any device activity |
| L2760 | early return -ENODEV | NO | N/A | ✅ | |
| L2790 | goto error (genpd_present fails, first domain) | NO (no prior adds) | N/A | ✅ | i=0, while(i--) does nothing |
| L2790 | goto error (genpd_present fails, i>0) | YES (prior device_adds) | NO | ❌ LEAK | error path only device_del, no put_device |
| L2801 | goto error (device_add fails, current i) | YES for previous, NO for current | NO | ❌ LEAK (previous devices) | previous adds leaked |
| L2820 | goto error (OPP fail after device_del) | YES (this and previous) | NO | ❌ LEAK | device_del done but no put_device |
| L2840 | goto error (genpd_add_provider fails) | YES (all domains added) | NO | ❌ LEAK | error while loop does device_del only |
| L2844 | return 0 (success) | YES (all) | NO (intentional) | ✅ | reference held for device lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

Error paths after `device_add()` call `device_del()` but fail to call `put_device()`, leaking the device reference taken by `device_add()`. The `while(i--)` loop in the error label only undoes provider flags and OPP tables but never drops the device reference, causing “inconsistent refcounting” on the genpd’s kobject.
```
