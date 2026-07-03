# REAL BUG: fs/btrfs/delayed-inode.c:2105 btrfs_destroy_delayed_inodes()

**Confidence**: MEDIUM | **Counter**: `$->refs.refs.counter`

## Reasoning

) | YES (release) but ⚠️ | ❓ **double put if __btrfs_kill_delayed_node puts** | Each node gets one get from first/next and one put from btrfs_release_delayed_node. If __btrfs_kill_delayed_node internally does a put, then prev_node would be released twice, causing the observed refcount underflow. |

## Full Response

```
[NEED_SOURCE] __btrfs_kill_delayed_node
[NEED_SOURCE] btrfs_next_delayed_node

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 2099-2105 (curr_node = btrfs_first_delayed_node; while loop entry) | Function return after loop | NO (curr_node NULL) | N/A | ✅ | No nodes processed; refcount untouched. |
| 2101‑2105 (loop iteration: curr_node non‑NULL, __btrfs_kill_delayed_node, prev=curr, curr=btrfs_next_delayed_node, btrfs_release_delayed_node(prev)) | Non‑NULL curr_node path | YES (first/next get) | YES (release) but ⚠️ | ❓ **double put if __btrfs_kill_delayed_node puts** | Each node gets one get from first/next and one put from btrfs_release_delayed_node. If __btrfs_kill_delayed_node internally does a put, then prev_node would be released twice, causing the observed refcount underflow. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The smatch warning “refcount excess put” at line 2105 (btrfs_release_delayed_node) strongly indicates that `__btrfs_kill_delayed_node` already decrements the node’s refcount, making the subsequent `btrfs_release_delayed_node` a double put.
```
