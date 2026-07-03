# REAL BUG: fs/ntfs3/namei.c:163 ntfs_link()

**Confidence**: HIGH | **Counter**: `$->i_count.counter`

## Reasoning

| __ntfs_link succeeds → after d_instantiate → goto out | success (goto out) | YES | NO | ❌ LEAK | No iput on success path |

## Full Response

```
| Line | Return Type   | GET Done? | PUT Done? | Balanced? | Notes |
|------|---------------|-----------|-----------|-----------|-------|
| L1516 early return -EIO | error (NVolShutdown) | NO (before get) | N/A | ✅ | No get yet |
| uname_len < 0 → goto out | error (goto out)       | NO (before get) | N/A | ✅ | Get hasn't happened |
| __ntfs_link fails → goto out (after iput) | error (goto out) | YES | YES (iput called) | ✅ | iput after mutex unlock |
| __ntfs_link succeeds → after d_instantiate → goto out | success (goto out) | YES | NO | ❌ LEAK | No iput on success path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ihold(vi)` is an unconditional get; on the success path after `d_instantiate`, the code falls through to the `out` label without calling `iput(vi)`, leaking the reference count.
```
