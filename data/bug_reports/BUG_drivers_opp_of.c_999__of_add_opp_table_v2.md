# REAL BUG: drivers/opp/of.c:999 _of_add_opp_table_v2()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

Given the available context and the warning pattern, this is **likely a real bug**: the error path unconditionally calls `_opp_remove_all_static()` even when no static OPPs were added, leading to an excess put on opp_table’s kref.

## Full Response

```
| Line | Return Type | GET Done? (opp_table kref) | PUT Done? (opp_table kref) | Balanced? | Notes |
|------|-------------|---------------------------|----------------------------|-----------|-------|
| L968 | early return 0 (already parsed) | NO | NO | ✅ | No OPP operations, no kref changes |
| L981 (goto remove_static_opp) | error after IS_ERR(opp) from loop | YES if count>0 (prior OPPs added each took a reference to opp_table), NO if count==0 | YES: `_opp_remove_all_static()` called, which presumably releases references for added OPPs. If count==0, does it still do a kref_put on opp_table? **Unknown** – needs source. | ❓ PENDING | If `_opp_remove_all_static()` unconditionally does a kref_put on opp_table, count==0 → excess put |
| L990 (goto remove_static_opp) | error, !count (no OPPs) | NO | YES: `_opp_remove_all_static()` | ❓ PENDING | Same as above. No OPPs added, but still calls remove_all. |
| L994 | return 0 (success) | YES (each added OPP holds an opp_table reference) | NO (released later when OPPs removed) | ✅ | Matches OPP lifecycle; no immediate put needed |

The `refcount excess put` warning likely triggers on the error path when **no OPPs were added** (count == 0) and yet `_opp_remove_all_static()` is called, which appears to perform a kref_put on opp_table’s kobj.kref without a corresponding kref_get in this function. The function holds no extra reference to opp_table; the success path relies on the OPPs’ references. Calling `_opp_remove_all_static()` in the error path when there are no OPPs to clean up may cause an unbalanced put, dropping the caller’s reference prematurely.

[NEED_SOURCE] _opp_remove_all_static
[NEED_SOURCE] _opp_add_static_v2

To confirm, I need the implementation of `_opp_remove_all_static()` to see whether it does an unconditional `kref_put(&opp_table->kobj.kref)` and how `_opp_add_static_v2()` manages opp_table’s refcount.

Given the available context and the warning pattern, this is **likely a real bug**: the error path unconditionally calls `_opp_remove_all_static()` even when no static OPPs were added, leading to an excess put on opp_table’s kref.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
```
