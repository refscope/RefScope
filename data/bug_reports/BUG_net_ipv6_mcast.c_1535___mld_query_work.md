# REAL BUG: net/ipv6/mcast.c:1535 __mld_query_work()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| else (len not matching V1 or V2) → goto out | error | YES | YES | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| Early skb checks (src addr, hop limit, RA) → kfree_skb | error/skip | NO (before get) | NO | ✅ | No idev acquired yet |
| `in6_dev_get()` returns NULL → kfree_skb | error | NO (get failed) | NO | ✅ | NULL idev, no put |
| `group_type != ANY && !MULTICAST` → goto out | error | YES (from `in6_dev_get`) | YES (at out) | ✅ | Single get/put |
| `len < MLD_V1_QUERY_LEN` → goto out | error | YES | YES | ✅ | |
| v1 block: `mld_process_v1()` returns <0 → goto out | error | YES | YES | ✅ | |
| **v1 block: `mld_process_v1()` returns >=0 → continues → falls through to out** | success | YES (from `in6_dev_get`) + if `mld_process_v1` does `in6_dev_put` it releases a ref | YES at out, but extra put if `mld_process_v1` already put → EXCESS | ❌ LEAK/EXCESS | `mld_process_v1` listed as a PUT in contracts → double-put on this path |
| v2 block: `pskb_may_pull(… srcs_offset)` fails → goto out | error | YES | YES | ✅ | |
| v2 block: group ANY, nsrcs != 0 → goto out (no sources allowed) | error | YES | YES | ✅ | |
| v2 block: group ANY, nsrcs == 0 → `mld_gq_start_work(idev)` → goto out | success | YES (+ extra get from `mld_gq_start_work`) | YES (one put) | extra get held, no underflow | Balanced (no excess put) |
| v2 block: group-specific (not ANY), pskb_may_pull for sources OK → loop → falls through to out | success | YES | YES | ✅ | |
| v2 block: pskb_may_pull for sources fails → goto out | error | YES | YES | ✅ | |
| else (len not matching V1 or V2) → goto out | error | YES | YES | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The contract marks `mld_process_v1` as a PUT (likely calls `in6_dev_put`). On the success path (err≥0) it already releases the idev reference, but the caller later executes the unconditional `in6_dev_put(idev)` at `out:`, causing a double-put and the reported "refcount excess put" at line 1535.
```
