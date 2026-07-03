# REAL BUG: fs/smb/client/connect.c:3590 cifs_mount_get_session()

**Confidence**: HIGH | **Counter**: `server->srv_count.counter`

## Reasoning

| L3574‑L3576 (falls through to out) | error (-EOPNOTSUPP) | YES (both server and ses) | NO | ❌ LEAK | server and ses references acquired but no put before returning an error; **this is the confirmed leak** |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3552 (goto out) | error (-EINVAL) | NO (server == NULL) | N/A | ✅ | no get happened |
| L3560 (goto out after IS_ERR(server)) | error | NO (server set to NULL) | N/A | ✅ | no valid server |
| L3568 (goto out after IS_ERR(ses)) | error | YES (server from cifs_get_tcp_session) | DEPENDS on cifs_get_smb_ses error‑handling | UNCERTAIN | contract says cifs_get_smb_ses can call cifs_put_tcp_session on some paths; if it always releases on error, path is balanced; otherwise leak |
| L3574‑L3576 (falls through to out) | error (-EOPNOTSUPP) | YES (both server and ses) | NO | ❌ LEAK | server and ses references acquired but no put before returning an error; **this is the confirmed leak** |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
After successful `cifs_get_tcp_session` and `cifs_get_smb_ses`, the persistent‑handles capability check sets an error code and falls through to `out` without releasing the acquired `server` refcount. No deferred cleanup or documented ownership transfer to `mnt_ctx` exists on this error path, so the reference is leaked.
```
