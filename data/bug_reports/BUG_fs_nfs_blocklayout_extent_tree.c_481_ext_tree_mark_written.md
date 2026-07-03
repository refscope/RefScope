# REAL BUG: fs/nfs/blocklayout/extent_tree.c:481 ext_tree_mark_written()

**Confidence**: HIGH | **Counter**: `$->be_device->ref.counter`

## Reasoning

4. **goto out between GET and PUT** – The `out` label at L462 only adjusts `bl_lwb`, unlocks, and calls `__ext_put_deviceids(&tmp)`. The split‑created extents are **not** in `tmp`, so their device refs are not released. L451 jumps past the merge block that would balance the earlier GET.

## Full Response

```
## 🔍 Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L417 | goto out (after __ext_tree_remove error) | NO (no split called) | N/A | ✅ | No split ref; removed extents handled by __ext_put_deviceids |
| L436 | goto out (after first ext_tree_split error) | NO (split failed) | N/A | ✅ | Conditional GET; error → no ref taken |
| L451 | goto out (after second ext_tree_split error) | YES (from prior successful first split) | NO | ❌ **LEAK** | First split succeeded, took device ref; second split fails → skips merge block that would release ref |
| L468 (success) | return err | YES (all splits) | YES (via ext_try_to_merge_* releasing ref) | ✅ | Normal completion |

**Additional detail**: When `be->be_f_offset < start`, the first `ext_tree_split(root, be, start)` succeeds (no goto out at L436). This split likely increments `be_device->ref.counter` for the new split‑off extent(s). Later, if `ext_f_end(be) > end`, the second `ext_tree_split(root, be, end)` is called. If that split fails, control jumps to `out` from L451, bypassing the mark‑and‑merge block (L455‑L458) where `ext_try_to_merge_left/right` would have decremented the extra device reference when merging the now‑written extent with neighbours. Thus the reference taken by the first successful split is never released, leading to a refcount leak on `be_device->ref.counter`. This matches the smatch warning at the original file’s line ~481, which is the `goto out` after the second split’s failure.

## 🔴 Pre‑Verdict Checklist

1. **“Held for device lifetime”?** – Not applicable; no probe‑remove pattern.  
2. **“Ownership transferred”?** – The split extents are stored in the tree; cleanup occurs later, but *the error path itself does not release the now‑permanent reference*, leaving an unbalanced get. No explicit cleanup code is invoked on the error path.  
3. **Unconditional GET?** – On success, `ext_tree_split` unconditionally takes a device reference for the newly created extent(s).  
4. **goto out between GET and PUT** – The `out` label at L462 only adjusts `bl_lwb`, unlocks, and calls `__ext_put_deviceids(&tmp)`. The split‑created extents are **not** in `tmp`, so their device refs are not released. L451 jumps past the merge block that would balance the earlier GET.

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  

Successful first `ext_tree_split` takes a device reference; subsequent failure of the second split exits via `goto out` without calling the merge functions that would drop the reference, causing a refcount leak on `be_device->ref.counter`.
```
