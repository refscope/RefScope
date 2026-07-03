# REAL BUG: net/sctp/auth.c:780 sctp_auth_set_key()

**Confidence**: HIGH | **Counter**: `cur_key->refcnt.refs.counter`

## Reasoning

| L764 | error (-ENOMEM) | YES | YES (`sctp_auth_shkey_release` called) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L727 | error (-EACCES) | NO (before `sctp_auth_shkey_create`) | N/A | ✅ | No reference acquired |
| L731 | error (-EACCES) | NO (before `sctp_auth_shkey_create`) | N/A | ✅ | |
| L739 | error (-ENOMEM) | NO (`cur_key` creation failed) | N/A | ✅ | `!cur_key` → GET=NO |
| L745 | error (-ENOMEM) | YES (`cur_key` created) | NO (only `kfree`, no `sctp_auth_shkey_release`) | ❌ LEAK | `kfree` bypasses proper refcount release |
| L753 | success (0)   | YES | YES (ownership transferred via `list_add`) | ✅ | List holds reference; no explicit put needed |
| L764 | error (-ENOMEM) | YES | YES (`sctp_auth_shkey_release` called) | ✅ | |
| L768 | success (0)   | YES | YES (ownership transferred via `list_add`) | ✅ | `sctp_auth_shkey_release(shkey)` handles old key but not needed for `cur_key` |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`cur_key` is obtained via `sctp_auth_shkey_create()` with refcount 1, but on the `key` allocation failure path (L745) it is freed with `kfree()` instead of `sctp_auth_shkey_release()`, leaving the reference counter unreleased (smatch sees no matching put).
```
