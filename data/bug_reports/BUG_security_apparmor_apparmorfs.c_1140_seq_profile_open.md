# REAL BUG: security/apparmor/apparmorfs.c:1140 seq_profile_open()

**Confidence**: HIGH | **Counter**: `proxy->count.count.refcount.refs.counter`

## Reasoning

| L1140 (success path) | Success return (error==0) | YES | NO | ❌ LEAK | No call to aa_put_proxy, refcount leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1140 (error path) | Error return after put | YES | YES | ✅ | Error branch calls aa_put_proxy, balance maintained |
| L1140 (success path) | Success return (error==0) | YES | NO | ❌ LEAK | No call to aa_put_proxy, refcount leaked |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
seq_profile_open acquires a reference via get_proxy_common_ref but only releases it on the error path; on success, the reference is never dropped.
```
