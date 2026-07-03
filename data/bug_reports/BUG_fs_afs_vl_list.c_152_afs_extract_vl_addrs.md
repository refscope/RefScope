# REAL BUG: fs/afs/vl_list.c:152 afs_extract_vl_addrs()

**Confidence**: LOW | **Counter**: `$->usage.refs.counter`

## Reasoning

is called at line 152, the reference count is already zero. This suggests that one of the callees (`afs_merge_fs_addr4` or `afs_merge_fs_addr6`) may have already released the address list on its error path, leading to a double-put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L98  | error (NULL) | NO (alloc failed) | N/A | ✅ | no alist allocated |
| L100 | success (alist, nr_addrs==0) | YES (refcount=1) | NO | ✅ | returns alist to caller; ownership transfer |
| L108 | goto error | YES | YES (at L152) | ✅ | error path properly releases |
| L116 | goto error | YES | YES (at L152) | ✅ | error path properly releases |
| L127 | goto error | YES | YES (at L152) | ✅ | error path properly releases |
| L135 | goto error | YES | YES (at L152) | ✅ | error path properly releases |
| L141 | goto error | YES | YES (at L152) | ✅ | error path properly releases |
| L150 | success (return alist) | YES | NO | ✅ | returns alist to caller; ownership transfer |

All paths inside this function appear balanced: every error path calls `afs_put_addrlist` exactly once, and success paths transfer ownership. The reported "excess put" is therefore not caused by a missing put in this function; it implies that when `afs_put_addrlist` is called at line 152, the reference count is already zero. This suggests that one of the callees (`afs_merge_fs_addr4` or `afs_merge_fs_addr6`) may have already released the address list on its error path, leading to a double-put.

[NEED_SOURCE] afs_merge_fs_addr4
[NEED_SOURCE] afs_merge_fs_addr6

VERDICT: REAL_BUG
CONFIDENCE: LOW
Merge functions may internally put the address list on failure, causing `afs_put_addrlist` at line 152 to operate on a zero refcount (excess put). Source needed to confirm.
```
