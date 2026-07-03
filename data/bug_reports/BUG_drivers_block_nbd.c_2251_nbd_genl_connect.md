# REAL BUG: drivers/block/nbd.c:2251 nbd_genl_connect()

**Confidence**: HIGH | **Counter**: `$->config_refs.refs.counter`

## Reasoning

| L2251 (success) | success return | YES (1 alloc + 2 start + 1 bonus = 4) | YES (1 via nbd_config_put) | ✅ (net 3 intended) | |

## Full Response

```
| Line | Return Type | GET Done? (config_refs) | PUT Done? (config_refs) | Balanced? | Notes |
|------|-------------|-------------------------|-------------------------|-----------|-------|
| L2077 | error (-EPERM) | NO (before any get) | NO | ✅ | early, no config involved |
| L2086 | error (-EINVAL) | NO | NO | ✅ | illegal index |
| L2091 | error (-EINVAL) | NO | NO | ✅ | missing SOCKETS attr |
| L2095 | error (-EINVAL) | NO | NO | ✅ | missing SIZE_BYTES attr |
| ~2111 | error (-EINVAL) | NO | NO | ✅ | device going down, refs not taken |
| ~2120 | error (PTR_ERR) | NO | NO | ✅ | nbd_dev_add failed, no config |
| ~2131 | error (-EBUSY) | NO | NO | ✅ | config_refs > 0 before alloc |
| ~2139 | error (ret) | NO (alloc_and_init failed, assume no config_refs set) | NO | ✅ | config alloc failed, no ref held |
| L2251 (via out before nbd_start_device) | error return | YES (1 from alloc_and_init) | YES (1 via nbd_config_put) | ✅ | alloc success, start_device not called |
| L2251 (after nbd_start_device failure) | error return | YES (1 alloc + 2 start = 3) | YES (1 via nbd_config_put) | ❌ LEAK | nbd_start_device increments twice unconditionally, only one put on error path |
| L2251 (success) | success return | YES (1 alloc + 2 start + 1 bonus = 4) | YES (1 via nbd_config_put) | ✅ (net 3 intended) | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
nbd_start_device unconditionally increments config_refs twice (contract), but the error path at L2251 only calls nbd_config_put once, leaking two references.
```
