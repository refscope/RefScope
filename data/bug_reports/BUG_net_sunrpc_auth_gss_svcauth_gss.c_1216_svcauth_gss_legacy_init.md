# REAL BUG: net/sunrpc/auth_gss/svcauth_gss.c:1216 svcauth_gss_legacy_init()

**Confidence**: HIGH | **Counter**: `rsip->h.ref.refcount.refs.counter`

## Reasoning

| L1219 (ret=SVC_COMPLETE) | success (fall through to out) | YES | **Excess** (cache_check already put + cache_put at out) | ❌ | double put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1165 | error (dup_netobj fail) | NO | N/A | ✅ | Before any rsi operations |
| L1175 | error (xdr_stream_decode_u32 fail) | NO | N/A | ✅ | No rsi yet |
| L1179 | error (xdr_inline_decode fail) | NO | N/A | ✅ | No rsi yet |
| L1183 | error (kmalloc fail) | NO | N/A | ✅ | No rsi yet |
| L1199 | error (rsi_lookup NULL) | NO (NULL, no ref taken) | N/A | ✅ | rsi_lookup returned NULL |
| L1202 | error (cache_check <0) | YES (via rsi_lookup) | YES (cache_check unconditional put) | ✅ | cache_check consumed the ref |
| ~L1209 (goto out) | error (svcauth_gss_proc_init_verf fails) | YES | **Excess** (cache_check already put + cache_put at out) | ❌ | double put |
| ~L1212 (goto out) | error (svcxdr_set_accept_stat fails) | YES | **Excess** (same) | ❌ | double put |
| ~L1215 (goto out) | error (svcxdr_encode_gss_init_res fails) | YES | **Excess** (same) | ❌ | double put |
| L1219 (ret=SVC_COMPLETE) | success (fall through to out) | YES | **Excess** (cache_check already put + cache_put at out) | ❌ | double put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`cache_check` is documented as unconditional put; after it returns >=0 the reference from `rsi_lookup` is already released. All subsequent paths that reach `cache_put` at `out:` (the success path and the three `goto out` failure paths) therefore execute an excess put.
```
