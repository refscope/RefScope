# REAL BUG: fs/btrfs/inode.c:7835 btrfs_invalidate_folio()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

**Lesson 4 applied**: The `btrfs_finish_ordered_io` call is a known pattern where the function takes over the ordered extent and internally releases it, so the caller must **not** put again. The path that calls it and then jumps to `next:` triggers a double put, exactly as the warning indicates.

## Full Response

```
[NEED_SOURCE] btrfs_finish_ordered_io
[NEED_SOURCE] btrfs_dec_test_ordered_pending

| Path | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| Early return (offset/length not full folio) | return; | NO | NO | ✅ | No ordered extent lookup yet. |
| Loop: `ordered == NULL`, `goto next` | continue loop | NO | NO (ordered is NULL, put skipped) | ✅ | |
| Loop: `ordered->file_offset > cur`, `goto next` | continue loop | YES | YES (btrfs_put_ordered_extent at `next:`) | ✅ | |
| Loop: `!btrfs_folio_test_ordered`, `goto next` | continue loop | YES | YES (btrfs_put_ordered_extent at `next:`) | ✅ | |
| Loop: `btrfs_dec_test_ordered_pending` true → `btrfs_finish_ordered_io(ordered)` → `goto next` | continue loop | YES | YES (btrfs_put_ordered_extent at `next:`) + **suspected internal put in btrfs_finish_ordered_io** | ❌ **EXCESS PUT** (double put) | The call to `btrfs_finish_ordered_io(ordered)` very likely consumes a reference (i.e., calls `btrfs_put_ordered_extent`), and the following `btrfs_put_ordered_extent` at `next:` causes a second put for the single reference acquired by `btrfs_lookup_first_ordered_range`. This results in refcount underflow. |
| After loop, fall-through return | return; | All gets were put in the loop (subject to above). | | ⚠️ Depends on above. | |

**Lesson 4 applied**: The `btrfs_finish_ordered_io` call is a known pattern where the function takes over the ordered extent and internally releases it, so the caller must **not** put again. The path that calls it and then jumps to `next:` triggers a double put, exactly as the warning indicates.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`btrfs_finish_ordered_io(ordered)` drops the ordered extent's reference; the unconditional `btrfs_put_ordered_extent()` at `next:` then puts again, causing an excess put and refcount underflow.
```
