# REAL BUG: drivers/infiniband/hw/mlx4/sysfs.c:689 add_port()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L1391 (return 0 success) | success return | YES | NO (ownership transferred to port, put later) | ✅ (deferred) | cdev released on port removal |

## Full Response

```
| Path (approx line) | Return Type | GET (cdev_alloc) Done? | PUT (cdev_put) Done? | Balanced? | Notes |
|-------------------|-------------|------------------------|----------------------|-----------|-------|
| L1326 (goto fail after kmalloc fail) | error return | NO | N/A | ✅ | before cdev_alloc |
| L1342 (goto free_port after cdev_alloc fails) | error return | NO (cdev_alloc failed, no object) | N/A | ✅ | no cdev reference |
| L1348 (goto free_cdev after cdev_add fails) | error return | YES | NO (cdev_del, no cdev_put) | ❌ LEAK | missing cdev_put |
| L1354 (goto free_cdev after device_create IS_ERR) | error return | YES | NO (cdev_del, no cdev_put) | ❌ LEAK | missing cdev_put |
| L1367 (goto free_device after fill_queue error) | error return | YES | NO (cdev_del, no cdev_put) | ❌ LEAK | missing cdev_put |
| L1375 (goto free_inbufs after init_port_console error) | error return | YES | NO (cdev_del, no cdev_put) | ❌ LEAK | missing cdev_put |
| L1391 (return 0 success) | success return | YES | NO (ownership transferred to port, put later) | ✅ (deferred) | cdev released on port removal |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
cdev_alloc returns with refcount 1; error paths after cdev_alloc (cdev_add fail, device_create fail, fill_queue fail, init_port_console fail) call cdev_del but omit cdev_put, leaking the cdev's kref.
```
