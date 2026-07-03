# REAL BUG: fs/btrfs/qgroup.c:4921 btrfs_qgroup_trace_subtree_after_cow()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

reloc_eb) once) | ❌ LEAK (error path) | qgroup_trace_subtree_swap is unconditional per contract; extra refs on reloc_eb and subvol_eb never released. Error ret < 0 leaks both refs; success may leak subvol_eb ref if ownership not transferred (but uncertain). At minimum error path is a clear leak. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4868 (return 0) | early bail (no accounting) | NO | N/A | ✅ | |
| L4871 (return 0) | early bail (not fs tree) | NO | N/A | ✅ | |
| L4876 (return 0) | early bail (no swapped) | NO | N/A | ✅ | |
| L4882 (goto out → L4919 return 0) | early bail (node not found) | NO | N/A | ✅ | no get, goto out after free_out; free_extent_buffer(NULL) harmless |
| L4906 (goto free_out → L4919 return ret) | IS_ERR guard on read_tree_block | NO (read_tree_block failed) | N/A | ✅ | reloc_eb = NULL, free_extent_buffer(NULL) safe |
| L4909–L4919 (normal flow, return ret) | after read_tree_block success + qgroup_trace_subtree_swap call | YES (read_tree_block ref + unconditional refcount_inc×2 from qgroup_trace_subtree_swap) | PARTIAL (only free_extent_buffer(reloc_eb) once) | ❌ LEAK (error path) | qgroup_trace_subtree_swap is unconditional per contract; extra refs on reloc_eb and subvol_eb never released. Error ret < 0 leaks both refs; success may leak subvol_eb ref if ownership not transferred (but uncertain). At minimum error path is a clear leak. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`qgroup_trace_subtree_swap` unconditionally increments two refcounts. On its error return the function falls through to `free_out` which only puts `reloc_eb` once, leaving the extra references from that swap call unreleased—a clear refcount leak.
```
