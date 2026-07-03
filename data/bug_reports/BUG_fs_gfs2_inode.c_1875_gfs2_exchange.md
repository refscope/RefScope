# REAL BUG: fs/gfs2/inode.c:1875 gfs2_exchange()

**Confidence**: HIGH | **Counter**: `$->gh_owner_pid->count.refs.counter`

## Reasoning

| success path | returns 0 via out_end_trans → out_gunlock → out_gunlock_r → out | ghs: YES, r_gh: YES | both fully released | ✅ | normal cleanup |

## Full Response

```
```
| Line (approx) | Return Type | GET Done? (holders) | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1747 | error (gfs2_rindex_update) | NO (no holders) | N/A | ✅ | early return, no refs acquired |
| L1754 | goto out (gfs2_glock_nq_init error) | r_gh GET failed, ghs not init | N/A | ✅ | r_gh uninitialized, safe |
| L1760 | goto out_gunlock_r (odip!=ndip, ok_to_move error) | r_gh YES (success), ghs not init | YES (out_gunlock_r) | ✅ | r_gh uninit'd via gfs2_glock_dq_uninit |
| L1765 | goto out_gunlock_r (second ok_to_move) | r_gh YES | YES | ✅ | |
| L1785 (mid-loop gfs2_glock_nq error) | goto out_gunlock, ghs[0..num_gh-1] all init'd, r_gh held if odip!=ndip | ghs: YES (init), r_gh: YES if odip!=ndip | ghs: NO for holders x..num_gh-1 (only 0..x-1 uninit'd); r_gh: NO | ❌ LEAK | holders x..num_gh-1 leak PID ref; r_gh also not released |
| L1791 (gfs2_glock_async_wait error, not -ESTALE) | goto out_gunlock, all ghs init'd, r_gh held if odip!=ndip | ghs: YES, r_gh: YES | ghs: all uninit'd ✅; r_gh: NO | ❌ LEAK (r_gh) | out_gunlock misses r_gh |
| L1794 (gfs2_glock_async_wait == -ESTALE) | goto again (retry loop) | N/A | N/A | ⚠️ | loops, may hit leak paths above |
| L1798 (errors: -ENOENT, unlink_ok, permission, trans_begin) | goto out_gunlock | ghs: YES, r_gh: YES if odip!=ndip | ghs: all uninit'd; r_gh: NO | ❌ LEAK (r_gh) | r_gh never released on these paths |
| L1831 (update_moved_ino, gfs2_dir_mvino errors) | goto out_end_trans → out_gunlock | same | ghs: all uninit'd; r_gh: NO | ❌ LEAK (r_gh) | |
| success path | returns 0 via out_end_trans → out_gunlock → out_gunlock_r → out | ghs: YES, r_gh: YES | both fully released | ✅ | normal cleanup |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Multiple error paths fail to uninit holders after gfs2_holder_init (PID ref leak), and paths after r_gh acquisition miss gfs2_glock_dq_uninit for r_gh.
```
```
