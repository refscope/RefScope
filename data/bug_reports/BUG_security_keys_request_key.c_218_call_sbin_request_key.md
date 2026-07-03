# REAL BUG: security/keys/request_key.c:218 call_sbin_request_key()

**Confidence**: HIGH | **Counter**: `$->usage.refs.counter`

## Reasoning

rmodehelper_keys | YES (user_session, keyring [initial ref]); `call_usermodehelper_keys` takes an **additional** keyring ref | YES (key_put(keyring) L211, key_put(user_session) L214) | ❌ LEAK | extra reference from call_usermodehelper_keys never released → keyring (and the authkey it holds) leak |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| error_us (goto at L134, return at L218) | error (look_up_user_keyrings failed) | NO (ret < 0) | N/A | ✅ | no references held |
| error_alloc (goto at L146, return at L218) | IS_ERR(keyring) | YES (user_session from look_up_user_keyrings) | YES (key_put(user_session) at L214) | ✅ | user_session released |
| error_link (goto at L152, return at L218) | ret < 0 from key_link | YES (user_session, keyring) | YES (key_put(keyring) L211, key_put(user_session) L214) | ✅ | key_link failure: no authkey ref |
| normal fall‑through (L196→L210, return L218) | return ret after call_usermodehelper_keys | YES (user_session, keyring [initial ref]); `call_usermodehelper_keys` takes an **additional** keyring ref | YES (key_put(keyring) L211, key_put(user_session) L214) | ❌ LEAK | extra reference from call_usermodehelper_keys never released → keyring (and the authkey it holds) leak |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`call_usermodehelper_keys` acquires an additional reference on `keyring`. The normal path after the helper falls through to `error_link`, which does a single `key_put(keyring)`. This leaves one reference held, leaking the keyring and consequently the authkey reference attached by `key_link`.
```
