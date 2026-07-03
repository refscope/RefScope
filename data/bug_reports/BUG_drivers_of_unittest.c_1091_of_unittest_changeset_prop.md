# REAL BUG: drivers/of/unittest.c:1091 of_unittest_changeset_prop()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

de_put` on that freed node again, causing a second parent decrement. Combined with the explicit `of_node_put(nchangeset)` at line 1091, the parent’s kref underflows, producing the “refcount excess put” warning. The apply-failure path and the revert/destroy fallthrough both trigger this double-put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1037-1039 (early return) | nchangeset NULL | NO (get returned NULL) | N/A | ✅ | No reference acquired |
| L1044 (goto end_changeset_destroy) | create_node failure | YES (nchangeset from L1036) | YES (at L1091) | ✅ | Normal cleanup, no np created |
| L1073-1074 (goto end_changeset_destroy after `of_changeset_apply` failure) | error apply | YES | YES (L1091) BUT **implicit extra PUT on nchangeset** from `np` double-release | ❌ **EXCESS PUT** | `of_node_put(np)` at L1070 freed np (refcount→0), triggering `of_node_release` that puts parent (nchangeset). Later `of_changeset_destroy` again puts the now-dangling np, repeating the parent put → excess decrement; explicit `of_node_put(nchangeset)` at L1091 then underflows. |
| L1077-1078 (goto end_revert_changeset) | second find_node failure | YES | YES (via revert→destroy→L1091) | ❌ **EXCESS PUT** (same as above) | Same double-release of np applies, as `of_node_put(np)` already ran. `end_revert_changeset` falls through to `of_changeset_destroy` which double-puts np. |
| L1084→L1089-1091 (fallthrough normal success) | success | YES | YES (L1091) | ❌ **EXCESS PUT** (same risk) | `np` already freed at L1070; subsequent `of_changeset_destroy` at L1090 acts on stale pointer → extra parent put. |

**Analysis:** The core problem is the premature `of_node_put(np)` at line 1070. `of_changeset_create_node` returns a node owned by the changeset; the caller must not release it. Dropping the reference frees the node, which calls `of_node_release` and decrements the parent (`nchangeset`). The changeset still holds a dangling pointer to the freed node. When `of_changeset_destroy` later iterates the changeset list, it calls `of_node_put` on that freed node again, causing a second parent decrement. Combined with the explicit `of_node_put(nchangeset)` at line 1091, the parent’s kref underflows, producing the “refcount excess put” warning. The apply-failure path and the revert/destroy fallthrough both trigger this double-put.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Premature `of_node_put(np)` before `of_changeset_apply` frees the node, leading to double release of parent `nchangeset` via `of_node_release` when `of_changeset_destroy` later processes the stale changeset entry.
```
