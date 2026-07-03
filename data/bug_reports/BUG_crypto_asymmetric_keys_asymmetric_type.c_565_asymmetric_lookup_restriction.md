# REAL BUG: crypto/asymmetric_keys/asymmetric_type.c:565 asymmetric_lookup_restriction()

**Confidence**: MEDIUM | **Counter**: `$->usage.refs.counter`

## Reasoning

| **~549** | **alloc success → fall through out, no key_put** | **YES** | **NO** | **❌ LEAK** | key ref held, not released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 509 | return alloc result (builtin_trusted) | NO | N/A | ✅ | no key_lookup |
| 513 | return alloc result (builtin_and_secondary) | NO | N/A | ✅ | |
| 517 | return ERR_PTR(-ENOMEM) | NO | N/A | ✅ | |
| ~550 | goto out (key_or_keyring not matched) | NO | N/A | ✅ | |
| 535 | goto out (kstrtos32 failure) | NO | N/A | ✅ | |
| ~538 | serial==0 && allow_null_key → key=NULL → alloc → out | NO | N/A | ✅ | no key ref |
| 542 | goto out (IS_ERR(key)) | NO | N/A | ✅ | key_lookup returned error |
| 548 | IS_ERR(ret) → key_put(key); fall through out | YES | YES | ✅ | error release |
| **~549** | **alloc success → fall through out, no key_put** | **YES** | **NO** | **❌ LEAK** | key ref held, not released |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
key_lookup() acquires a reference; on the path where asymmetric_restriction_alloc() succeeds, no key_put() is called, creating a refcount leak unless the alloc function takes ownership, which cannot be verified.
```
