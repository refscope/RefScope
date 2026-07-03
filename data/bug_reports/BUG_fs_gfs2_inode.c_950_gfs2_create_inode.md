# REAL BUG: fs/gfs2/inode.c:950 gfs2_create_inode()

**Confidence**: LOW | **Counter**: `$->a_refcount.refs.counter`

## Reasoning

aths: after both `__gfs2_set_acl` calls succeed, the local pointers are set to NULL, so any later `fail_free_acls` is harmless. The double‑put risk could arise if **the same ACL pointer is put twice by two different mechanisms**. In `fail_gunlock4` → `fail_free_acls` the pointer is NULL, but what if

## Full Response

```
## Path Table

We need to trace all return paths, accounting for the ACL references acquired via `posix_acl_create()` (each returns 1 reference) and the unconditional get in `__gfs2_set_acl()` (increments refcount). The matching release is `posix_acl_release()` (safe on NULL, but an extra call leads to refcount excess). The warning targets `a_refcount.refs.counter` (POSIX ACL refcount), line ~950 likely inside `fail_free_acls`. I'll enumerate every exit point.

I will label the GET for an ACL as follows:
- **ACL_GET**: `posix_acl_create()` → each non‑NULL result holds a reference (refcount +1). This is a standard “create gives reference” pattern.
- **SET_GET**: `__gfs2_set_acl()` → unconditional get (per contract). On success, we immediately release the original reference and NULLify the local pointer.

| Line (approx) | Return Type | ACL_PTR State | GET from create? | Extra GET from set_acl? | PUT Called? | Balanced? | Notes |
|---------------|-------------|---------------|------------------|-------------------------|-------------|-----------|-------|
| L720 (error: `gfs2_qa_get(dip)`) | `return error` | before acl_create | NO | NO | N/A | ✅ | acl not yet obtained |
| L725 (`gfs2_rindex_update` fail → `goto fail`) | `fail` (error) | before acl_create | NO | NO | N/A | ✅ | |
| L730 (`gfs2_glock_nq_init` fail → `goto fail`) | `fail` | before acl_create | NO | NO | N/A | ✅ | |
| L736 (`create_ok` fail → `goto fail_gunlock`) | `fail_gunlock` | before acl_create | NO | NO | N/A | ✅ | |
| L740 (`gfs2_dir_search` not ENOENT → `goto fail_gunlock`) | `fail_gunlock` | before acl_create | NO | NO | N/A | ✅ | |
| L743 (`gfs2_dir_search` IS_ERR but not ENOENT → `goto fail_gunlock`) | `fail_gunlock` | before acl_create | NO | NO | N/A | ✅ | |
| L750 (`gfs2_diradd_alloc_required` fail → `goto fail_gunlock`) | `fail_gunlock` | before acl_create | NO | NO | N/A | ✅ | |
| L755 (`new_inode` NULL → `goto fail_gunlock`) | `fail_gunlock` | before acl_create | NO | NO | N/A | ✅ | |
| L760 (`posix_acl_create` error → `goto fail_gunlock`) | `fail_gunlock` | acl_create returned error | NO (error) | NO | N/A | ✅ | acl not allocated |
| L765 (`gfs2_qa_get(ip)` error → `goto fail_free_acls`) | `fail_free_acls` | after acl_create, acls present | YES (both) | NO | YES (both released) | ✅ | |
| L830 (`alloc_dinode` error → `goto fail_free_inode`) | → `fail_free_inode` → `fail_free_acls` | acls present | YES (both) | NO | YES (both released) | ✅ | |
| L835 (`gfs2_glock_get(i_gl)` error → `goto fail_dealloc_inode`) | → `fail_dealloc_inode` → ... → `fail_free_acls` | acls present | YES (both) | NO | YES (both released) | ✅ | |
| L839 (`gfs2_glock_get(io_gl)` error → `goto fail_dealloc_inode`) | same | acls present | YES (both) | NO | YES (both released) | ✅ | |
| L845 (`insert_inode_locked4` error → `goto fail_gunlock2`) | → `fail_gunlock2` → ... → `fail_free_acls` | acls present | YES (both) | NO | YES (both released) | ✅ | |
| L850 (`gfs2_glock_nq_init(io_gl)` error → `goto fai
```
