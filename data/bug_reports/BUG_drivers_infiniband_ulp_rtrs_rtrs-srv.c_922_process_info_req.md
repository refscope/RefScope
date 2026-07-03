# REAL BUG: drivers/infiniband/ulp/rtrs/rtrs-srv.c:922 process_info_req()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L922 (success) | return 0 | YES | NO (held for lifetime) | ⚠️ | intentionally kept for path lifetime |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L822 | error (return err) | NO (before gets) | N/A | ✅ | post_recv_path fail |
| L827 | error (return -EINVAL) | NO (before gets) | N/A | ✅ | invalid pathname check |
| L833 | error (return -EPERM) | NO (before gets) | N/A | ✅ | duplicate pathname |
| L840 | error (return -ENOMEM) | NO (before gets) | N/A | ✅ | rwr alloc fail |
| L848 | goto rwr_free (err=-ENOMEM) | NO (before gets) | N/A | ✅ | tx_iu alloc fail |
| L879 | goto iu_free (create_path_files fail) | NO (before L880-881) | N/A | ✅ | gets haven’t happened yet |
| L885 | goto iu_free (change_state fail) | YES (L880-881) | NO | ❌ LEAK | after `kobject_get` and `get_device`, no put |
| L899 | goto iu_free (path_up fail) | YES | NO | ❌ LEAK | same, after gets |
| L915-916 | iu_free (post_send fail) | YES | NO | ❌ LEAK | same, after gets |
| L922 (success) | return 0 | YES | NO (held for lifetime) | ⚠️ | intentionally kept for path lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Error paths after `kobject_get` (L880) and `get_device` (L881) leak the acquired references; `goto iu_free` at L885/L899/L915 does not call `kobject_put`/`put_device`.
```
