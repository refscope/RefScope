# REAL BUG: net/sunrpc/auth_gss/svcauth_gss.c:582 rsc_parse()

**Confidence**: LOW | **Counter**: `rscp->h.ref.refcount.refs.counter`

## Reasoning

**⚠️ The only uncertain path is when `rsc_update()` returns NULL.** In that case, the original reference obtained by `rsc_lookup()` is lost if `rsc_update` does not release it. Without the rsc_update source, this is a cross‑function unknown.

## Full Response

```
[NEED_SOURCE] rsc_update

## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L479 | goto out (len < 0) | NO (rscp still NULL) | N/A | ✅ | before rsc_lookup |
| L482 | goto out (dup_to_netobj fail) | NO | N/A | ✅ | |
| L488 | goto out (get_expiry fail) | NO | N/A | ✅ | |
| L493 | goto out (!rscp) | NO (lookup returned NULL) | N/A | ✅ | rsc_lookup failed |
| L498 | goto out (rv == -EINVAL) | YES (rscp from L491 is non‑NULL) | YES (via out label, line 583‑584) | ✅ | rscp != NULL; out calls cache_put |
| L508‑L573 | various goto out within the else (uid/gid/mech/principal) | YES (rscp non‑NULL after L491) | YES (out label puts rscp) | ✅ | all jump to out, which puts |
| L579 → **rsc_update returns NULL** | out label (status=0 then out) | YES (rscp **was** non‑NULL from lookup, now overwritten to NULL) | **NO** (rscp is NULL at out, no put) | **❌ LEAK** | rsc_update may consume the old reference or not – unknown without source |
| L579 → rsc_update returns non‑NULL | out label | YES (rscp non‑NULL, either same or new) | YES (cache_put called at L583‑584) | ✅ | normal success path |

**⚠️ The only uncertain path is when `rsc_update()` returns NULL.** In that case, the original reference obtained by `rsc_lookup()` is lost if `rsc_update` does not release it. Without the rsc_update source, this is a cross‑function unknown.

VERDICT: UNCLEAR  
CONFIDENCE: LOW  
One‑line reasoning: The leak depends on whether rsc_update() releases the reference of the old rscp when it returns NULL; without its source this cannot be determined.

[NEED_SOURCE] rsc_update
```
