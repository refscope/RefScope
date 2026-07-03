# REAL BUG: kernel/cpu.c:3048 cpuhp_sysfs_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L3047 | success (all per‑cpu devices registered) | YES (get_cpu_device called for each possible CPU, dev != NULL for each) | NO | ❌ LEAK | none of the acquired per‑cpu devices are put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3029 | error (cpu_smt_sysfs_init fail) | NO (before any get) | N/A | ✅ | |
| L3036 | error (sysfs_create_group on dev_root fails) | YES (bus_get_dev_root non‑NULL) | YES (put_device L3034 already executed) | ✅ | dev_root properly put unconditionally before the ret check |
| L3045 | error (sysfs_create_group on per‑cpu device fails) | YES (get_cpu_device succeeded, dev != NULL) | NO | ❌ LEAK | missing put_device(dev) |
| L3047 | success (all per‑cpu devices registered) | YES (get_cpu_device called for each possible CPU, dev != NULL for each) | NO | ❌ LEAK | none of the acquired per‑cpu devices are put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
get_cpu_device calls get_device (standard get/put semantics) but cpuhp_sysfs_init never calls put_device on the per‑cpu devices it acquires – both the error‑return and success paths leak their references.
```
