# REAL BUG: fs/nfs/delegation.c:542 nfs_inode_set_delegation()

**Confidence**: MEDIUM | **Counter**: `$->cred->usage.counter`

## Reasoning

Given the warning and the code flow, it is highly likely that `nfs_detach_delegations_locked` already releases the delegation’s reference, making the later put redundant.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L437 (early return after kmalloc fail) | error | NO (allocation failed) | N/A | ✅ | no delegation, no cred get |
| L462→add_new→out (old==NULL) | success | NO (no delegation ref get beyond initial alloc; initial ref counted as owned) | NO (delegation=NULL at out) | ✅ | delegation added, no need to put |
| L469 goto out (stateid match, inplace update) | success | YES (nfs_update_inplace_delegation get/put on cred, delegation freed) | YES (__nfs_free_delegation releases delegation, including cred put) | ✅ | delegation freed, cred released |
| L482 goto out (duplicate delegation) | error? | NO (delegation=NULL, new deleg not used) | YES (nfs_put_delegation(freeme) on new deleg) | ✅ | new deleg reference dropped |
| L485 goto out (RETURNING already set) | goto out | NO (delegation non-NULL, not freed elsewhere) | YES (__nfs_free_delegation) | ✅ | freeing new deleg |
| L489 goto out (detach fails) | goto out | NO (detach didn't take ref) | YES (__nfs_free_delegation) | ✅ | freeing new deleg |
| L490→add_new→out (detach succeeds) | success | YES (old_del ref held by inode pointer before detach, detach may or may not put) | YES (nfs_put_delegation(freeme) on old_del) | ❓ | depends on detach internals; warning suggests excess put |

[NEED_SOURCE] nfs_detach_delegations_locked

`nfs_detach_delegations_locked()` likely unlinks `old_delegation` from lists and NULLs the inode’s delegation pointer. If this function also calls `nfs_put_delegation()` or otherwise drops the reference that was held by the pointer, then the subsequent `nfs_put_delegation(freeme)` at line 542 (L527 in snippet) is an excess put. The warning “refcount excess put on $->cred->usage.counter” at that line is consistent with a double-put on the old delegation’s refcount, leading to a freed cred being put again.

Given the warning and the code flow, it is highly likely that `nfs_detach_delegations_locked` already releases the delegation’s reference, making the later put redundant.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`nfs_detach_delegations_locked` likely drops the old delegation’s reference, causing `nfs_put_delegation(freeme)` to over-decrement the refcount and trigger an excess cred put. Source needed to confirm, but the warning points to a real double-put bug.

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] nfs_detach_delegation

--- [NEED_SOURCE r2] ---

[NEED_SOURCE] nfs_inode_set_delegation
```
