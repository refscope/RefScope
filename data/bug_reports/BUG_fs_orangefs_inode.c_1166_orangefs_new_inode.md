# REAL BUG: fs/orangefs/inode.c:1166 orangefs_new_inode()

**Confidence**: HIGH | **Counter**: `$->a_refcount.refs.counter`

## Reasoning

| L1165| success      | YES                     | YES               | YES (one put each)        | YES (one put each) | ✅                  | Inode returned; extra refs held by inode, released on eviction. |

## Full Response

```
```
| Line | Return Type  | GET Done? (default_acl) | GET Done? (acl) | PUT Done? (default_acl) | PUT Done? (acl) | Balanced?          | Notes |
|------|--------------|-------------------------|-----------------|--------------------------|-----------------|--------------------|-------|
| L1105| error        | NO (before any create)  | NO               | N/A                      | N/A             | ✅                  | Early -ENOMEM, no ACLs allocated |
| L1113| goto out_iput| NO (not called)         | NO               | YES (out_iput puts if non-NULL) | YES (out_iput puts if non-NULL) | ✅ | posix_acl_create error – initial refs (if any) released |
| L1120| goto out_iput| NO                      | NO               | YES                      | YES             | ✅                  | orangefs_inode_getattr error – only initial refs released |
| L1128| goto out_iput| YES (unconditional get from __orangefs_set_acl, error path) | NO (not called yet) | YES (one put at out_iput) | YES (one put for initial ref) | ❌ LEAK on default_acl | `__orangefs_set_acl` took extra ref; error after the call → not stored in inode → extra ref leaked |
| L1134| goto out_iput| YES (from earlier successful set) | YES (unconditional get from __orangefs_set_acl, error path) | YES (one put each) | YES (one put each) | ❌ LEAK on both ACLs | Both `__orangefs_set_acl` calls returned error; extra refs not stored → leaked |
| L1138| goto out_iput| YES (successful set)    | YES (successful set) | YES (one put each) | YES (one put each) | ⚠️ Potential leak? | set_acl succeeded → inode owns extra ref; iput will evict and release. Behaviour correct, but smatch may still flag. |
| L1165| success      | YES                     | YES               | YES (one put each)        | YES (one put each) | ✅                  | Inode returned; extra refs held by inode, released on eviction. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`__orangefs_set_acl` is an unconditional get (contract). On error paths L1128 and L1134, the call has already incremented the ACL refcount but the function reports failure – without storing the ACL in the inode. The existing `out_iput` cleanup only releases the initial reference from `posix_acl_create`, leaking the extra reference taken by the failed set_acl.
```
```
