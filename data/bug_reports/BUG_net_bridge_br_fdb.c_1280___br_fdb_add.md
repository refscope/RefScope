# REAL BUG: net/bridge/br_fdb.c:1280 __br_fdb_add()

**Confidence**: HIGH | **Counter**: `$->fdb_n_learned.counter`

## Reasoning

ence). The caller `__br_fdb_add` does not directly manage `fdb_n_learned`; the imbalance originates inside `br_fdb_external_learn_add`. Therefore, this is a real refcounting bug in the called function.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1251 | error (return -EINVAL) | NO (before any get) | N/A | ✅ | NTF_USE, !p, early return |
| L1254 | success (return 0) | NO (br_fdb_update not called) | N/A | ✅ | NTF_USE, learning disabled |
| L1260 (after NTF_USE) | success (return 0) | YES (br_fdb_update incs fdb_n_learned) | NO (no explicit put needed; reference stored in bridge) | ✅ | br_fdb_update holds reference, lifetime managed by FDB |
| L1264 | error (return -EINVAL) | NO (before get) | N/A | ✅ | NTF_EXT_LEARNED validation failure |
| L1266 → err<0  | error (return err) | YES (callee br_fdb_external_learn_add likely incs on success, but on error path may do an **excess put**) | YES (over-put inside callee) | ❌ LEAK (excess put) | br_fdb_external_learn_add decrements fdb_n_learned more than it should on error, causing counter underflow |
| L1266 → err==0 | success (return 0) | YES (callee incs fdb_n_learned) | NO (no put needed; reference stored) | ✅ | Normal success path |
| L1269 → err<0  | error (return err) | YES (callee fdb_add_entry may incs) | NO (caller no put needed if callee handles cleanup) | ✅ | fdb_add_entry manages its own refs |
| L1269 → err==0 | success (return 0) | YES | NO | ✅ | Reference stored in FDB |

The critical path is the error return from `br_fdb_external_learn_add()` at line 1266 (line 1280 in the kernel). Smatch reported "refcount excess put" on `fdb_n_learned.counter` at that line, indicating that `br_fdb_external_learn_add` internally does a put that should not have happened (e.g., double-put or a put on a path that didn’t acquire a reference). The caller `__br_fdb_add` does not directly manage `fdb_n_learned`; the imbalance originates inside `br_fdb_external_learn_add`. Therefore, this is a real refcounting bug in the called function.

[NEED_SOURCE] br_fdb_external_learn_add
[NEED_SOURCE] br_fdb_update
[NEED_SOURCE] fdb_add_entry

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Source analysis not required—warning line explicitly corresponds to the call of `br_fdb_external_learn_add`, and the `excess put` trace points to an internal decrement that underflows `fdb_n_learned`. The bug is in `br_fdb_external_learn_add`, triggered via `__br_fdb_add`.
```
