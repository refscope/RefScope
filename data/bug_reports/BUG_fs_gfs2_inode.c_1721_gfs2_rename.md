# REAL BUG: fs/gfs2/inode.c:1721 gfs2_rename()

**Confidence**: HIGH | **Counter**: `$->gh_owner_pid->count.refs.counter`

## Reasoning

This loop only uninit’s holders `0` to `x-1`. The holder at index `x` is **not** uninit’d, leaking the PID reference taken by its earlier `gfs2_holder_init()`. `gfs2_glock_nq()` does not release the holder on error, and no other cleanup occurs for that holder, so this is a real refcount leak.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1497 | return 0 (ip==nip) | NO (before get) | N/A | ✅ | |
| L1502 | return error (rindex_update) | NO | N/A | ✅ | |
| L1506 | return error (qa_get) | NO | N/A | ✅ | |
| L1524 | goto out (glock_nq_init r_gh err) | NO (conditional get failed) | N/A | ✅ | r_gh not initialized |
| L1531 | goto out_gunlock_r (ok_to_move err) | YES (r_gh) | YES (at out_gunlock_r) | ✅ | |
| L1580 | goto out_gunlock (glock_nq err at index x) | YES (ghs[0..x] all init) | **NO** for ghs[x] (only 0..x-1 uninit) | ❌ LEAK | failed holder skipped in cleanup loop |
| L1585 | goto out_gunlock (async_wait err) | YES (all ghs) | YES (all uninit, x==num_gh) | ✅ | |
| L1595..L1705 | multiple goto out_gunlock | YES (all ghs) | YES | ✅ | x==num_gh after successful loop |
| L1719 | out_end_trans path | YES (all ghs) | YES | ✅ | |
| All `out_gunlock_r` paths | as appropriate | YES (r_gh if initialized) | YES | ✅ | |
| `out` path (after qa_get error) | N/A | NO | YES (qa_put) | ✅ | |

**Analysis of the leak path:**  
In the `again` block, `gfs2_holder_init()` is called for all holders in `ghs[]`, acquiring a PID reference for each. The subsequent `for` loop calls `gfs2_glock_nq()`; if this fails at index `x`, the code jumps to `out_gunlock`. The cleanup there runs:

```c
while (x--) {
    if (gfs2_holder_queued(ghs + x))
        gfs2_glock_dq(ghs + x);
    gfs2_holder_uninit(ghs + x);
}
```

This loop only uninit’s holders `0` to `x-1`. The holder at index `x` is **not** uninit’d, leaking the PID reference taken by its earlier `gfs2_holder_init()`. `gfs2_glock_nq()` does not release the holder on error, and no other cleanup occurs for that holder, so this is a real refcount leak.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`gfs2_glock_nq` failure in the `for` loop skips `gfs2_holder_uninit` for the failed holder, leaking the `gh_owner_pid` reference.
```
