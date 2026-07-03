# REAL BUG: drivers/infiniband/hw/ionic/ionic_ibdev.c:371 ionic_create_ibdev()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

| L352 | SUCCESS return        | YES                          | YES (owned by ibdev)             | YES                 | YES (ownership transferred) | ✅ YES     | later uncleared by ib_unregister_device / re‑association             |

## Full Response

```
```
| Line | Return Type           | GET (ionic_lif_netdev) Done? | GET (ib_device_set_netdev) Done? | PUT (dev_put) Done? | ib_set_netdev ref released? | Balanced? | Notes                                                                 |
|------|-----------------------|------------------------------|----------------------------------|---------------------|-----------------------------|-----------|-----------------------------------------------------------------------|
| L312 | ERROR return          | NO (before get)              | NO (before call)                 | N/A                 | N/A                         | ✅ YES     |                                                                       |
| L322 | goto err_reset        | NO                           | NO                               | N/A                 | N/A                         | ✅ YES     | get calls not reached yet                                             |
| L325 | goto err_admin        | NO                           | NO                               | N/A                 | N/A                         | ✅ YES     | get calls not reached yet                                             |
| L342 | goto err_admin (rc!=0)| YES                          | NO (call failed, no ref taken)   | YES (dev_put before if) | N/A                         | ✅ YES     | ionic_lif_netdev ref released; ib_device_set_netdev acquired nothing  |
| L350 | goto err_register     | YES                          | YES (call succeeded)             | YES                 | ❌ NO                       | ❌ LEAK    | ib_device_set_netdev acquired netdev ref, not released on error path |
| L352 | SUCCESS return        | YES                          | YES (owned by ibdev)             | YES                 | YES (ownership transferred) | ✅ YES     | later uncleared by ib_unregister_device / re‑association             |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ib_device_set_netdev()` succeeds before `ib_register_device` fails, the error path (goto err_register → err_admin) never releases the netdev reference held by the ib device.
```
