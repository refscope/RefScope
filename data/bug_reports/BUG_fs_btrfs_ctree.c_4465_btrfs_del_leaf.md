# REAL BUG: fs/btrfs/ctree.c:4465 btrfs_del_leaf()

**Confidence**: MEDIUM | **Counter**: `leaf->refs.refs.counter`

## Reasoning

| L4465 → end (all paths) | any return | YES (refcount_inc unconditional) | **CONDITIONAL** | ⚠️ POTENTIAL LEAK | free_extent_buffer_stale may not decrement if I/O outstanding or refcount ≠ 2; refcount_inc is unconditional, so failure to put leaks reference |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4447 (early ret) | error return | NO (before get) | N/A | ✅ | refcount_inc not yet called |
| L4465 → end (all paths) | any return | YES (refcount_inc unconditional) | **CONDITIONAL** | ⚠️ POTENTIAL LEAK | free_extent_buffer_stale may not decrement if I/O outstanding or refcount ≠ 2; refcount_inc is unconditional, so failure to put leaks reference |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  

free_extent_buffer_stale is documented as conditional (`conditional_on_path`, releases only when specific refcount/I/O conditions are met). The unconditional `refcount_inc(&leaf->refs)` at L4463 is not balanced by an unconditional put; the only put call at L4465 may skip the decrement, causing a refcount leak on leaf.
```
