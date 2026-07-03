# REAL BUG: drivers/pwm/core.c:1393 pwm_unexport_child()

**Confidence**: HIGH | **Counter**: `pwm_dev->kobj.kref.refcount.refs.counter`

## Reasoning

| L1394 | success (return 0) | YES (device_find_child incremented ref) | YES (twice — explicit put_device then device_unregister calls put_device again) | ❌ EXCESS PUT | double release of the same reference |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1376-1377 | error (return -ENODEV) | NO (before device_find_child) | N/A | ✅ | bit not set, early return |
| L1380-1381 | error (return -ENODEV) | NO (device_find_child returns NULL, no ref acquired) | N/A | ✅ | conditional get failed |
| L1394 | success (return 0) | YES (device_find_child incremented ref) | YES (twice — explicit put_device then device_unregister calls put_device again) | ❌ EXCESS PUT | double release of the same reference |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
device_find_child acquires a reference; the code then calls both put_device(pwm_dev) and device_unregister(pwm_dev) (which internally calls put_device again), causing a double release and refcount underflow. Remove the explicit put_device to fix.
```
