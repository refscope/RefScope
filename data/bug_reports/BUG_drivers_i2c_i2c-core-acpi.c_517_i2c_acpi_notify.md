# REAL BUG: drivers/i2c/i2c-core-acpi.c:517 i2c_acpi_notify()

**Confidence**: HIGH | **Counter**: `adapter->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L514 | NOTIFY_OK   | YES (i2c_acpi_find_adapter_by_adev) | NO (at L517) after possible double-put | ❌ EXCESS PUT | acpi_unbind_one(L516) contract says →put_device; if it puts, then L517 put_device is extra → underflow |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes                                                              |
|------|-------------|-----------|-----------|-----------|--------------------------------------------------------------------|
| L485 | NOTIFY_OK   | NO (before any GET) | N/A       | ✅        | ADD case: i2c_acpi_get_info failed → break                         |
| L489 | NOTIFY_OK   | NO (GET returned NULL) | N/A   | ✅        | ADD case: adapter = NULL, break                                    |
| L492 | NOTIFY_OK   | YES (i2c_acpi_find_adapter_by_handle) | YES (put_device at L496) | ✅ | ADD case: got ref, put it, balanced                                |
| L508 | NOTIFY_OK   | NO (acpi_device_enumerated false) | N/A | ✅        | REMOVE case: early break, no GETs                                  |
| L511 | NOTIFY_OK   | YES (i2c_acpi_find_client_by_adev) | YES (put_device at L513) | ✅ | Client get/put balanced (independent adapter ref)                  |
| L514 | NOTIFY_OK   | YES (i2c_acpi_find_adapter_by_adev) | NO (at L517) after possible double-put | ❌ EXCESS PUT | acpi_unbind_one(L516) contract says →put_device; if it puts, then L517 put_device is extra → underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
i2c_acpi_find_adapter_by_adev acquires a reference on adapter->dev. Contract of acpi_unbind_one explicitly says it can call put_device. If that happens, the following put_device at L517 is a double put, causing the refcount underflow reported by smatch.
```
```
