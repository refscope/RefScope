# REAL BUG: fs/btrfs/qgroup.c:2564 qgroup_trace_new_subtree_blocks()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| ~2560 | success (0)   | YES | NO (need_cleanup==false) | ❌ LEAK | normal return, need_cleanup false |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~2475 | error (-EUCLEAN) | NO (before GET) | N/A  | ✅ | level sanity check |
| ~2489 | error (-EUCLEAN) | NO (before GET) | N/A  | ✅ | cur_level==root_level |
| ~2505 | success (0)   | NO (before GET) | N/A  | ✅ | old generation, skip |
| ~2512 | error (PTR_ERR) | NO (before GET) | N/A  | ✅ | read_node_slot failure |
| ~2527 | error (goto cleanup) | YES | NO (need_cleanup==false) | ❌ LEAK | need_cleanup false → no free_extent_buffer |
| ~2527 | error (goto cleanup) | YES | YES (need_cleanup==true) | ⚠️ potentially unbalanced | extra ref may not be fully released |
| ~2540 | error (recursive ret<0, goto cleanup) | YES | NO (need_cleanup==false) | ❌ LEAK | need_cleanup false → no put |
| ~2540 | error (recursive ret<0, goto cleanup) | YES | YES (need_cleanup==true) | ⚠️ potentially unbalanced |  |
| ~2560 | success (0)   | YES | NO (need_cleanup==false) | ❌ LEAK | normal return, need_cleanup false |
| ~2560 | success (0)   | YES | YES (need_cleanup==true) | ⚠️ potentially unbalanced |  |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Need_cleanup remains false when dst_path->nodes[cur_level] already exists; after the unconditional GET by qgroup_trace_extent_swap, cleanup skips free_extent_buffer → leaked refcount on every such path (error or success).
```
