# REAL BUG: fs/ceph/inode.c:2196 ceph_readdir_prepopulate()

**Confidence**: HIGH | **Counter**: `$->i_count.counter`

## Reasoning

| L2180+ (loop end → out label return err) | return err | N/A (all loop paths already accounted) | N/A | N/A | leak already captured in splice_dentry error path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2009 | early return (readdir_prepopulate_inodes_only) | NO | N/A | ✅ | no inode ref held |
| ~L2053 (d_alloc failure) | goto out | NO (no inode allocated yet) | N/A | ✅ | |
| ~L2078 (ceph_get_inode IS_ERR) | goto out | NO (get failed) | N/A | ✅ | IS_ERR(in) guards no ref |
| ~L2090 (ceph_fill_inode error) | goto next_item | YES (inode from ceph_get_inode) | YES (iput(in)) | ✅ | explicit iput in error block |
| ~L2110 (ceph_security_xattr_deadlock) | goto next_item | YES (inode) | YES (iput(in)) | ✅ | iput before goto |
| **~L2115 (splice_dentry error)** | **goto next_item** | **YES (inode from ceph_get_inode)** | **NO 🚨** | **❌ LEAK** | **inode ref held, never dropped** |
| L2120 (success fall-through) | next_item (loop continues) | YES (transferred to dentry) | N/A (ownership transfer) | ✅ | inode attached, no explicit put needed |
| L2180+ (loop end → out label return err) | return err | N/A (all loop paths already accounted) | N/A | N/A | leak already captured in splice_dentry error path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
splice_dentry error (err < 0) at ~L2115 jumps to next_item without iput(in), leaking the inode reference obtained from ceph_get_inode.
```
