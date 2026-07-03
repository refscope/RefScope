# REAL BUG: drivers/infiniband/core/cm.c:3235 cm_mra_handler()

**Confidence**: LOW | **Counter**: `$->refcount.refs.counter`

## Reasoning

Given the uncertainty, I cannot conclusively state REAL_BUG or FALSE_POSITIVE until the callee’s behavior is clarified.

## Full Response

```
| Path | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| `return -EINVAL` (after `!cm_id_priv`) | error | NO (cm_acquire_mraed_id returned NULL) | N/A | ✅ | No reference acquired |
| `goto out` in `IB_CM_REQ_SENT` failure | error | YES | YES (cm_deref_id) | ✅ | Explicit put in `out:` label |
| `goto out` in `IB_CM_REP_SENT` failure | error | YES | YES (cm_deref_id) | ✅ | |
| `goto out` in `IB_CM_ESTABLISHED` failure | error | YES | YES (cm_deref_id) | ✅ | |
| `goto out` in `IB_CM_MRA_REQ_RCVD`/`_REP_RCVD` / default | error | YES | YES (cm_deref_id) | ✅ | |
| `return 0` (after `cm_queue_work_unlock`) | success | YES | **UNKNOWN** (depends on `cm_queue_work_unlock` contract) | ❓ | Contract says `cm_queue_work_unlock` is conditional on path → may skip `cm_deref_id`. If so, ref NOT released here → LEAK. |

**Contract of `cm_queue_work_unlock`**: `conditional_on_path; →cm_deref_id(put)`. This means the put is not unconditional; there are paths where it may NOT call `cm_deref_id`. The success path calls `cm_queue_work_unlock(cm_id_priv, work)` without checking for possible failure to release the reference. If `cm_queue_work_unlock` does not always release, the refcount is leaked on that success path, consistent with the smatch warning at line 3235.

Without the source of `cm_queue_work_unlock`, I cannot determine whether it *always* eventually calls `cm_deref_id` (e.g., even on queue failures) or only conditionally. The contract explicitly flags it as conditional, so the current success path looks suspect.

**[NEED_SOURCE] cm_queue_work_unlock** – to resolve the condition.

Given the uncertainty, I cannot conclusively state REAL_BUG or FALSE_POSITIVE until the callee’s behavior is clarified.

```
VERDICT: UNCLEAR
CONFIDENCE: LOW
```
**Reason**: `cm_queue_work_unlock` contract is conditional; if it ever fails to put the reference, the success path leaks the `cm_acquire_mraed_id` reference. Without the callee’s source, can’t confirm whether the put is guaranteed.
```
