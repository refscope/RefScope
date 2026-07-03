# REAL BUG: fs/smb/client/connect.c:4438 cifs_sb_tlink()

**Confidence**: HIGH | **Counter**: `$->tl_count.counter`

## Reasoning

| L4423 (construct ok) | return tlink | YES | NO (caller holds) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4369 (early return) | return cifs_get_tlink(…) | YES (via cifs_get_tlink) | N/A (caller holds) | ✅ | multiuser off, returns master with ref |
| L4380 (alloc fail) | return ERR_PTR(-ENOMEM) | NO | N/A | ✅ | no ref taken |
| L4391 (kfree + goto wait) | goto wait_for_construction | YES (on newtlink) | NO (on newtlink) | ❌ LEAK | cifs_get_tlink(newtlink) held, kfree without put |
| L4399 (wait_err) | return ERR_PTR(-ERESTARTSYS) | YES (on tlink) | YES (cifs_put_tlink) | ✅ | |
| L4402 (good tcon) | return tlink | YES | NO (caller holds) | ✅ | success, ref passed to caller |
| L4407 (error expiry) | return ERR_PTR(err) | YES | YES (cifs_put_tlink) | ✅ | |
| L4421 (construct err) | return ERR_PTR(err) | YES | YES (cifs_put_tlink) | ✅ | |
| L4423 (construct ok) | return tlink | YES | NO (caller holds) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Path that discards freshly allocated `newtlink` after `cifs_get_tlink(newtlink)` fails to call `cifs_put_tlink(newtlink)` before `kfree(newtlink)`, leaking the reference.
```
