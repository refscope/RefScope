# REAL BUG: fs/btrfs/relocation.c:5648 btrfs_recover_relocation()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L5647 | function end | YES | NO | ❌ LEAK | |

## Full Response

```
| Line | Return Type | GET Done? (reloc_root ref) | PUT Done? | Balanced? | Notes |
|------|-------------|-----------------------------|-----------|-----------|-------|
| L5494 | return -ENOMEM | NO (before get) | N/A | ✅ | |
| L5505 | goto out (search slot error) | NO (not yet acquired in this iteration) | N/A | ✅ | previously added roots in list, freed at out |
| L5523 | goto out (IS_ERR) | NO (get failed) | N/A | ✅ | |
| L5535 | goto out (fs_root !-ENOENT) | YES (root in list) | YES (list frees at out) | ✅ | `list_add` earlier |
| L5538 | goto out (mark_garbage fail) | YES (root in list) | YES (list frees) | ✅ | |
| L5553 | goto out (list empty) | YES (any root in list) | YES (list frees) | ✅ | |
| L5558 | goto out (rc alloc fail) | YES (roots in list) | YES (list frees) | ✅ | |
| L5565 | goto out (no extent root) | YES (roots in list) | YES (list frees) | ✅ | |
| L5570 | goto out_end (chunk start fail) | YES (roots in list) | YES (list frees via out_end→out) | ✅ | |
| L5577 | goto out_unset (join trans fail) | YES (roots in list) | YES (list frees via out_unset→out_end→out) | ✅ | |
| L5598 | goto out_unset (IS_ERR fs_root) | YES (root put back in list) | YES (list frees) | ✅ | `list_add_tail` reclaims |
| L5607 | goto out_unset (__add_reloc_root fail) | YES (root put back in list) | YES (list frees) | ✅ | `list_add_tail` reclaims |
| L5609‑5610 | loop continues (success path) | YES (original ref not released) | NO | ❌ LEAK | `btrfs_read_tree_root` gave a ref; after `list_del` the list no longer holds it; `btrfs_grab_root` adds a new ref, but the original ref is never `put` |
| L5615 | `goto out_unset` (commit fail) | YES (all processed roots leaked) | NO | ❌ LEAK | |
| L5624 | `goto out_clean` (second join fail) | YES | NO | ❌ LEAK | |
| L5636+ (out_clean fall-through) | out_unset→out_end→out→return | YES | NO | ❌ LEAK | `free_reloc_roots` only frees list contents; processed roots are no longer in the list |
| L5646 | `return ret;` | YES | NO | ❌ LEAK | |
| L5647 | function end | YES | NO | ❌ LEAK | |

**PRE‑VERDICT CHECKLIST**
1. “Held for device lifetime”? Not applicable; this is a filesystem helper, not a probe. Error paths in the second loop do not release the original `reloc_root` reference.
2. “Ownership transferred”? No. The code does `btrfs_grab_root` to obtain a separate reference for `fs_root->reloc_root`, leaving the caller’s reference undropped. No explicit transfer of the original ref exists.
3. Unconditional GET? `btrfs_read_tree_root` acquires a reference on every success (not IS_ERR). The success path unconditionally holds a root ref that must be released.
4. `goto out` between GET and PUT? Yes: after the loop, `goto out_unset` (L5615, L5624) and the final fall‑through path all leave the original ref unreleased.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
After `btrfs_read_tree_root` provides a referenced `reloc_root`, the second loop’s success path removes it from the `reloc_roots` list but never calls `btrfs_put_root` for the origin
```
