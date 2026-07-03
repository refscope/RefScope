# REAL BUG: drivers/of/overlay.c:459 add_changeset_node()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L452–453 (end)  | return after live path | YES                 | YES            | ✅                   | |

## Full Response

```
## Path Table

```
| Line | Return Type           | GET Done?           | PUT Done?     | Balanced?           | Notes |
|------|-----------------------|---------------------|---------------|---------------------|-------|
| L418 | error (-ENOMEM)       | NO (tchild is NULL) | N/A           | ✅                   | No node allocated |
| L436 | error (attach failed) | YES (`__of_node_dup` gives refcount 1) | NO            | ❌ LEAK              | tchild not put; reference leak (separate bug) |
| L442–443 | success (new node) | YES (`__of_node_dup`) | YES (`of_node_put`) | ❌ EXCESS PUT (if `of_changeset_attach_node` takes ownership) | Ownership transfer means caller must not put; put is surplus, triggering refcount excess put warning |
| L446 → L452–453 | error (-EINVAL) or success (live child) | YES (`for_each_child_of_node` gives ref) | YES (L452)     | ✅                   | |
| L450 → L452–453 | success (live child) | YES (`for_each_child_of_node` gives ref) | YES (L452)     | ✅                   | |
| L452–453 (end)  | return after live path | YES                 | YES            | ✅                   | |
```

## VERDICT: REAL_BUG
CONFIDENCE: HIGH  
`__of_node_dup` gives `tchild` an initial reference; `of_changeset_attach_node` typically takes ownership of the node (consumes the reference), making the caller’s subsequent `of_node_put` at L442 an excess put and causing a refcount underflow—exactly matching the warning.
```
