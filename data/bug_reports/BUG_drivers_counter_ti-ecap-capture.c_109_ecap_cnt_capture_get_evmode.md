# REAL BUG: drivers/counter/ti-ecap-capture.c:109 ecap_cnt_capture_get_evmode()

**Confidence**: HIGH | **Counter**: `counter->parent->power.usage_count.counter`

## Reasoning

4. goto out between GET and PUT? None. But the **unconditional** execution of pm_runtime_put_sync after an unchecked get is the problem.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L110 | u8 return   | Conditional (YES if pm_runtime_get_sync() ≥ 0, NO if < 0) | YES (L109) | ❌ On get-failure path: GET=NO, PUT=YES → excess put | get return value not checked; unconditional put after get. If get fails, refcount not incremented, but put decrements → underflow. |

**Pre-Verdict Checklist**
1. "Held for device lifetime"? N/A – not a probe / remove pair; this is a sysfs callback.
2. "Ownership transferred"? No – no list/hash add, no deferred cleanup.
3. Unconditional GET? **Contract says conditional**: pm_runtime_get_sync increments **only** on success (ret ≥ 0). Return value **not checked** → for a failed call, GET did not happen.
4. goto out between GET and PUT? None. But the **unconditional** execution of pm_runtime_put_sync after an unchecked get is the problem.

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
`pm_runtime_get_sync` return value is ignored; if it fails (<0) the usage count is not incremented, yet the function unconditionally calls `pm_runtime_put_sync`, causing an excess put (refcount underflow). The fix is to check the return value and only call `pm_runtime_put_sync` on success, or not call it on failure.
```
