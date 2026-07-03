# REAL BUG: drivers/scsi/libsas/sas_discover.c:508 sas_discover_domain()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L508 (error path, error != 0) | void return | YES (sas_get_port_device) | YES (sas_put_device) | ❌ EXCESS | sas_discover_end_dev / callee likely already sas_put_device on error, leading to double put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L463 (early return: port->port_dev) | void return | NO (before any get) | N/A | ✅ | No device obtained |
| L465 (early return: sas_get_port_device error) | void return | NO (get failed) | N/A | ✅ | Error return before dev is assigned |
| L506 (normal end, error == 0) | void return | YES (sas_get_port_device) | NO | ✅ | Reference held on port->port_dev, no excess |
| L508 (error path, error != 0) | void return | YES (sas_get_port_device) | YES (sas_put_device) | ❌ EXCESS | sas_discover_end_dev / callee likely already sas_put_device on error, leading to double put |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
sas_discover_domain error path calls sas_put_device at line 508, but internal discovery functions like sas_discover_end_dev often already release the device on error, causing a refcount excess put.
```
