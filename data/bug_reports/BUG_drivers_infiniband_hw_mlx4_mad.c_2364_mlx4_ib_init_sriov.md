# REAL BUG: drivers/infiniband/hw/mlx4/mad.c:2364 mlx4_ib_init_sriov()

**Confidence**: HIGH | **Counter**: `$->iov_parent->kref.refcount.refs.counter`

## Reasoning

4. `goto out` between GET and PUT? – `goto sysfs_err` after the get leads to a label that lacks `unregister_sysfs`.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2293: return 0 (early if not mfunc) | early return | NO (before get) | N/A | ✅ | |
| L2303: return 0 (slave) | early return | NO | N/A | ✅ | |
| L2314: goto paravirt_err (alias_guid init fails) | error path | NO (sysfs not called) | N/A | ✅ | |
| L2323: goto sysfs_err (register sysfs fails) | error path | YES (unconditional get per contract) | NO (unregister not called) | ❌ LEAK | `mlx4_ib_device_unregister_sysfs` is skipped |
| L2335: goto demux_err (loop error after sysfs) | error path | YES (sysfs succeeded) | YES (unregister at L2342) | ✅ | |
| L2338: goto free_pv → demux_err | error path | YES | YES | ✅ | |
| L2346: return 0 (success) | success | YES | NO (deferred to device removal) | ✅ (design) | held for lifetime, cleaned up in remove |

🔴 Pre-verdict checklist:
1. "Held for device lifetime"? – Only applies to success return; error path in probe (L2323) does not benefit from that and leaks.
2. "Ownership transferred"? – No documented cleanup that would cover the error path at L2323; no transfer.
3. Unconditional GET? – Contract explicitly states unconditional → GET=YES on failure path.
4. `goto out` between GET and PUT? – `goto sysfs_err` after the get leads to a label that lacks `unregister_sysfs`.

VERDICT: REAL_BUG

CONFIDENCE: HIGH

One-line reasoning: Unconditional `mlx4_ib_device_register_sysfs` at L2323 increments the parent kref, but the error path `goto sysfs_err` returns without calling the matching `mlx4_ib_device_unregister_sysfs`, leaking the reference.
```
