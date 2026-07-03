# REAL BUG: drivers/opp/of.c:1097 _of_add_table_indexed()

**Confidence**: LOW | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

ver acquired by `_of_add_opp_table_v2` (or `v1`). The call to `_add_opp_table_indexed` likely does not give a reference or the v2 function releases its own reference internally on failure, making the caller’s optional put double the release. In either case, the put is unbalanced on the error path.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1080 (IS_ERR(opp_table)) | error (PTR_ERR) | NO (no object returned) | N/A | ✅ | Early return on error, no reference to release. |
| L1085-1096: opp_table->np true, `_of_add_opp_table_v2()` returns error (ret ≠ 0) | error | UNKNOWN (depends on v2 internals) | YES (L1097) | ❌ LIKELY LEAK/EXCESS | Warning indicates `excess put` on this path → v2 did not take a reference, so put is invalid. The refcount likely drops from 0 to -1. |
| L1085-1096: opp_table->np true, `_of_add_opp_table_v2()` returns success (ret = 0) | success (0) | UNKNOWN | NO | ❓ | If v2 took a ref, it’s retained on success (normal). No put needed. |
| L1088-1096: opp_table->np false, `_of_add_opp_table_v1()` returns error | error | UNKNOWN | YES (L1097) | ❌ LIKELY EXCESS | Same issue as v2 error path. |
| L1088-1096: opp_table->np false, `_of_add_opp_table_v1()` returns success | success | UNKNOWN | NO | ❓ | |

**[NEED_SOURCE] _of_add_opp_table_v2**  
**[NEED_SOURCE] _of_add_opp_table_v1**  
**[NEED_SOURCE] _add_opp_table_indexed**

Given the `excess put` warning targeting the kref counter after `dev_pm_opp_put_opp_table()` on L1097, the error path puts a reference that was never acquired by `_of_add_opp_table_v2` (or `v1`). The call to `_add_opp_table_indexed` likely does not give a reference or the v2 function releases its own reference internally on failure, making the caller’s optional put double the release. In either case, the put is unbalanced on the error path.

VERDICT: REAL_BUG  
CONFIDENCE: LOW  
`dev_pm_opp_put_opp_table()` is called unconditionally on error from `_of_add_opp_table_v2/v1`, but the get inside those callees either never happens on failure or is already released, causing an extra kref decrement (excess put).
```
