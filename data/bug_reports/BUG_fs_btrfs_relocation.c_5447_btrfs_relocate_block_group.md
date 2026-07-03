# REAL BUG: fs/btrfs/relocation.c:5447 btrfs_relocate_block_group()

**Confidence**: HIGH | **Counter**: `bg->refs.refs.counter`

## Reasoning

| ~L5445 | success (non-remap) | YES | NO | YES | ✅ | do_nonremap_reloc, no extra get |

## Full Response

```
| Line | Return Type | GET (lookup)? | GET (remap)? | PUT Done? | Balanced? | Notes |
|------|-------------|---------------|--------------|-----------|-----------|-------|
| L5325 | error | NO | NO | N/A | ✅ | `return -EUCLEAN` before lookup |
| L5329 | error | NO | NO | N/A | ✅ | `return ret` after wait_on_bit |
| L5331 | error | NO | NO | N/A | ✅ | `return -EINTR` if closing |
| L5335 | error (lookup failed) | NO | NO | N/A | ✅ | `bg = NULL`, no ref |
| ~L5349 | error | YES | NO | YES | ✅ | pinned_by_swapfile; explicit `btrfs_put_block_group(bg)` |
| ~L5353 | error | YES | NO | YES | ✅ | alloc_reloc_control fails; explicit put |
| ~L5362 | goto out_put_bg | YES | NO | YES | ✅ | reloc_chunk_start fails; out_put_bg puts initial ref |
| ~L5380 | goto out | YES | NO | YES | ✅ | inc_block_group_ro fails; out_put_bg put |
| ~L5386 | goto out | YES | NO | YES | ✅ | alloc_path fails; out_put_bg put |
| ~L5394 | goto out | YES | NO | YES | ✅ | delete_block_group_cache fails; out_put_bg put |
| ~L5402 | goto out | YES | NO | YES | ✅ | create_reloc_inode fails; out_put_bg put |
| ~L5422 | goto out | YES | NO | YES | ✅ | move_existing_remaps fails; out_put_bg put (no extra get yet) |
| ~L5424 | goto out | YES | NO (fails) | YES | ✅ | start_block_group_remapping fails; conditional get → no extra ref; balanced |
| **~L5429** | **goto out (do_remap_reloc fails)** | **YES** | **YES (remap get succeeded)** | **NO** | **❌ LEAK** | **start_block_group_remapping succeeded, took extra ref; error path only releases initial ref → extra ref is leaked** |
| ~L5431 | success (after do_remap_reloc ok & btrfs_delete_unused_bgs) | YES | YES | NO | ❓ SUSPECT | do_remap_reloc might eventually release extra ref, but no explicit put |
| ~L5445 | success (non-remap) | YES | NO | YES | ✅ | do_nonremap_reloc, no extra get |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`start_block_group_remapping` takes an extra reference on the block group when it succeeds; the following `goto out` on `do_remap_reloc` failure only calls `btrfs_put_block_group` once (the initial lookup reference), leaving the remap reference leaked and causing the inconsistent refcounting.
```
