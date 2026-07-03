# REAL BUG: fs/xfs/xfs_iops.c:277 xfs_generic_create()

**Confidence**: HIGH | **Counter**: `$->a_refcount.refs.counter`

## Reasoning

| L227 | success (fall through to out_free_acl) | YES (both GET) | YES (1 release each, inode holds extra ref) | ✅ | balanced, refs held by inode |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L177 | error return | NO (before acl) | N/A  | ✅ | early dev check, no acl |
| L184 | error return | NO | N/A  | ✅ | posix_acl_create failed, no acl |
| L188 | goto out_free_acl | NO (acl created but no __xfs_set_acl) | YES (posix_acl_release both) | ✅ | safe, no extra ref held |
| L196‑L204 | goto out_free_acl (xfs_create/tmpfile error) | NO | YES | ✅ | acls released, no set |
| L206 | goto out_cleanup_inode (xfs_inode_init_security error) | NO | YES (via out_free_acl) | ✅ | no set, acls released |
| L210 | goto out_cleanup_inode (__xfs_set_acl default error) | YES (default_acl GET) | NO (only 1 release via out_free_acl, need 2) | ❌ LEAK | unconditional get from __xfs_set_acl not released |
| L215 | goto out_cleanup_inode (__xfs_set_acl acl error, default_acl succeeded) | YES (both GET) | NO (acl needs 2 releases, only 1 via out_free_acl) | ❌ LEAK | acl ref leaked |
| L215 | goto out_cleanup_inode (acl error, default_acl not set) | YES (acl GET only) | NO (acl needs 2 releases) | ❌ LEAK | same leak |
| L227 | success (fall through to out_free_acl) | YES (both GET) | YES (1 release each, inode holds extra ref) | ✅ | balanced, refs held by inode |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`__xfs_set_acl` unconditionally increments the refcount on the posix_acl. When it fails, the error paths via `out_cleanup_inode` → `out_free_acl` release only one reference per acl, leaking the reference taken by `__xfs_set_acl`. The warning line 277 (return from `out_free_acl`) reflects the inconsistent refcount at function exit.
```
