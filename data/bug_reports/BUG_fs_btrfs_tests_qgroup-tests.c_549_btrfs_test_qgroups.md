# REAL BUG: fs/btrfs/tests/qgroup-tests.c:549 btrfs_test_qgroups()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L549 | return ret    | YES            | NO        | ❌ LEAK | normal exit after successful tests, btrfs_free_dummy_root does not release root->node |

## Full Response

```
| Line | Return Type  | GET Done?      | PUT Done? | Balanced? | Notes |
|------|---------------|----------------|-----------|-----------|-------|
| L471 | return -ENOMEM | NO (before get) | N/A       | ✅ | fs_info alloc fail, root not yet allocated |
| L478 | goto out      | NO (before get) | N/A       | ✅ | root alloc fail, alloc_test_extent_buffer not called yet |
| L493 | goto out      | NO (IS_ERR guard) | N/A     | ✅ | alloc_test_extent_buffer returned ERR_PTR, ref not taken |
| L499 | goto out      | YES            | NO        | ❌ LEAK | tmp_root alloc fail after successful root->node get |
| L507 | goto out      | YES            | NO        | ❌ LEAK | btrfs_insert_fs_root fail after get |
| L513 | goto out      | YES            | NO        | ❌ LEAK | second tmp_root alloc fail after get |
| L519 | goto out      | YES            | NO        | ❌ LEAK | second insertion fail after get |
| L523 | goto out      | YES            | NO        | ❌ LEAK | test_no_shared_qgroup fail after get |
| L525 | goto out      | YES            | NO        | ❌ LEAK | test_multiple_refs fail after get |
| L549 | return ret    | YES            | NO        | ❌ LEAK | normal exit after successful tests, btrfs_free_dummy_root does not release root->node |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
All return paths after a successful `alloc_test_extent_buffer()` leak the extent_buffer refcount because `btrfs_free_dummy_root(root)` does not release `root->node` for dummy roots (it calls `btrfs_put_root` which for dummy roots only kfree's the root without calling `free_root_extent_buffers`). The missing explicit `free_extent_buffer(root->node)` violates the standard Btrfs test pattern.
```
