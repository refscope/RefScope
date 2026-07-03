# REAL BUG: net/netfilter/nf_nat_core.c:384 nf_nat_used_tuple_harder()

**Confidence**: HIGH | **Counter**: `$->ct_general.use.refs.counter`

## Reasoning

| L372-373 path: nf_ct_kill returns FALSE | fall-through to out | YES | YES (nf_ct_put at L375) | ✅ | nf_ct_kill did not drop ref, so single put is correct |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L339-342 | early return (before get) | NO (before get) | N/A | ✅ | No reference held |
| L352    | return false (get failed) | NO (NULL from nf_conntrack_find_get) | N/A | ✅ | Conditional get, no ref on NULL |
| L359    | goto out (IP_CT_DIR_ORIGINAL) | YES | YES (nf_ct_put at L375) | ✅ | Normal cleanup |
| L362    | goto out (WARN_ON_ONCE) | YES | YES (nf_ct_put at L375) | ✅ | |
| L365    | goto out (!nf_nat_may_kill) | YES | YES (nf_ct_put at L375) | ✅ | |
| L368    | goto out (!nf_seq_has_advanced) | YES | YES (nf_ct_put at L375) | ✅ | |
| L372-373 path: nf_ct_kill returns TRUE | fall-through to out | YES | YES (nf_ct_put at L375) | ❌ **EXCESS PUT** | nf_ct_kill consumed the reference internally, then extra nf_ct_put |
| L372-373 path: nf_ct_kill returns FALSE | fall-through to out | YES | YES (nf_ct_put at L375) | ✅ | nf_ct_kill did not drop ref, so single put is correct |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`nf_ct_kill()` is the standard netfilter kill function that both deletes the conntrack and drops the reference held by the caller. The `out:` label unconditionally calls `nf_ct_put(ct)`, causing a double-put (excess put) whenever `nf_ct_kill(ct)` returns true. The fix is to only call `nf_ct_put` when `nf_ct_kill` fails, or to adjust the kill to not consume the reference.
```
