# REAL BUG: net/ceph/osd_client.c:3344 check_linger_pool_dne()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| 3340–3344 (else → send_linger_map_check called) | void return | YES (conditional get in callee) | NO | ⚠️ (put deferred) | a later `__linger_cancel` will release the acquired reference |

## Full Response

```
[NEED_SOURCE] __linger_cancel
[NEED_SOURCE] linger_reg_commit_complete
[NEED_SOURCE] send_linger_map_check

| Line | Return Type | GET Done? (send_linger_map_check) | PUT Done? (__linger_cancel) | Balanced? | Notes |
|------|-------------|-----------------------------------|-----------------------------|-----------|-------|
| 3324–3332 (register_gen true → inner if → __linger_cancel) | void return | NO | YES | ❌ Excess Put | `send_linger_map_check` never called, but `__linger_cancel` performs a `kref_put` on the map‑check reference |
| 3333–3339 (register_gen false, map_dne_bound ≠ 0, epoch ≥ bound → __linger_cancel) | void return | NO | YES | ❌ Excess Put | same unmatched put |
| 3333–3339 (register_gen false, map_dne_bound ≠ 0, epoch < bound) | void return | NO | NO | ✅ | no get, no put |
| 3340–3344 (else → send_linger_map_check called) | void return | YES (conditional get in callee) | NO | ⚠️ (put deferred) | a later `__linger_cancel` will release the acquired reference |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`check_linger_pool_dne` calls `__linger_cancel` (which does a `kref_put`) in paths where `send_linger_map_check` was never invoked, leading to a refcount drop without a matching acquisition.
```
