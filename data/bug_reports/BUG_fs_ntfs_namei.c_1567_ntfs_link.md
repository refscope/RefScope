# REAL BUG: fs/ntfs/namei.c:1567 ntfs_link()

**Confidence**: HIGH | **Counter**: `$->i_count.counter`

## Reasoning

| ~1560 (fallthrough after L1559) | success return err==0 | YES | NO | ❌ LEAK | after d_instantiate, mutex unlocks, no iput(vi) |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (ihold at L1538) | PUT Done? (iput) | Balanced? | Notes |
|------|-------------|---------------------------|-------------------|-----------|-------|
| 1525 | error return -EIO | NO (before get) | N/A | ✅ | |
| 1533 | goto out (uname_len<0) | NO (before get) | N/A | ✅ | |
| 1548 | error goto out (__ntfs_link failed) | YES | YES (iput at L1546) | ✅ | explicit iput inside error block |
| ~1560 (fallthrough after L1559) | success return err==0 | YES | NO | ❌ LEAK | after d_instantiate, mutex unlocks, no iput(vi) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
ihold(vi) at line 1538 unconditionally increments the inode refcount; the success path after d_instantiate() returns without iput(vi), leaking the extra reference.
```
