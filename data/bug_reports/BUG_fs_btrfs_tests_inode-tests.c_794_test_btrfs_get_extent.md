# REAL BUG: fs/btrfs/tests/inode-tests.c:794 test_btrfs_get_extent()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

root) ; 2) btrfs_free_dummy_root(root) → btrfs_put_root | ❌ **EXCESS PUT** | No `refcount_inc` on root when storing into inode; iput drops reference not accounted for, then test cleanup drops initial ref → refcount underflow. Warning at line ~794 likely inside `btrfs_free_dummy_root` or its put. |

## Full Response

```
| Path | Return Type | GET Done? (root from `btrfs_alloc_dummy_root`) | PUT Done? (root) | Balanced? | Notes |
|------|-------------|-----------------------------------------------|-------------------|-----------|-------|
| inode or fs_info alloc fails → `goto out` before root alloc | error | NO (root not allocated) | NO (btrfs_free_dummy_root(ERR_PTR), likely no‑op) | ✅ | |
| `root = btrfs_alloc_dummy_root(fs_info)` returns ERR_PTR → `goto out` | error | NO (root is error pointer) | NO (free skips error pointer) | ✅ | |
| `root->node` alloc fails → `goto out` (after root alloc, before `BTRFS_I(inode)->root = root`) | error | YES (alloc returns refcount 1) | YES (btrfs_free_dummy_root once) | ✅ | iput sees inode->root still NULL/original; no root put |
| After `BTRFS_I(inode)->root = root;` – every `goto out` (all test failures and the final `ret = 0` fallthrough) | error or success | YES (ref = 1) | **YES × 2**: 1) iput(inode) → btrfs_evict_inode → btrfs_put_root(inode->root) ; 2) btrfs_free_dummy_root(root) → btrfs_put_root | ❌ **EXCESS PUT** | No `refcount_inc` on root when storing into inode; iput drops reference not accounted for, then test cleanup drops initial ref → refcount underflow. Warning at line ~794 likely inside `btrfs_free_dummy_root` or its put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`BTRFS_I(inode)->root = root;` takes no reference on the root, but `iput(inode)` internally puts the root, leading to an extra put when the test later calls `btrfs_free_dummy_root(root)`, causing the observed refcount excess put on `root->refs`.
```
