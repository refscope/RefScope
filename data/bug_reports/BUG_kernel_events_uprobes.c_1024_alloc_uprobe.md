# REAL BUG: kernel/events/uprobes.c:1024 alloc_uprobe()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

- The “held for device lifetime” concept does not apply here; the object is abandoned before being published, but the refcount must still be released via its put routine.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L999 | error       | NO (before refcount_set) | N/A       | ✅        | kzalloc failed |
| L1018 | error       | YES (refcount_set at L1008) | NO        | ❌ **LEAK** | uprobe refcount = 1, but only cur_uprobe is put; kfree(uprobe) without put_uprobe |
| L1020→1021→1024 | success (returning cur_uprobe) | YES (refcount_set at L1008) | NO        | ❌ **LEAK** | uprobe refcount = 1, kfree(uprobe) without put_uprobe; cur_uprobe’s ref is transferred to caller |
| L1024 (cur_uprobe == uprobe) | success | YES (refcount_set + insert_uprobe’s get) | callers responsibility | ✅ | Both references accounted: tree holds one, caller receives one |

## Analysis

- **insert_uprobe** contract (the tracked GET) increments the refcount on the uprobe it **inserts**. When `cur_uprobe != uprobe`, the new `uprobe` is **not** inserted, so `insert_uprobe` does **not** increment `uprobe`’s refcount. The new `uprobe` still holds the initial reference from `refcount_set` at L1008.
- Error paths at L1018 and L1020–1021 free `uprobe` with `kfree()` without calling `put_uprobe()`, leaking the initial refcount.
- The “held for device lifetime” concept does not apply here; the object is abandoned before being published, but the refcount must still be released via its put routine.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`alloc_uprobe()` sets a refcount to 1 but frees the object via `kfree()` on error paths without calling `put_uprobe()`, leaking the initial reference.
```
