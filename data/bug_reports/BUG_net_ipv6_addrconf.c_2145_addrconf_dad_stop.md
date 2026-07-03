# REAL BUG: net/ipv6/addrconf.c:2145 addrconf_dad_stop()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

- goto between GET and PUT? No goto, but the else branch chooses the wrong put function.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2133 (temporary address) | void (ipv6_del_addr(ifp)) | YES (caller's ref on ifp) | YES (via ipv6_del_addr) – also drops DAD work/link refs | ⚠️ Possibly unbalanced but not highlighted; temp addresses may expect full deletion | Temporary branch; warning not on this line. |
| L2143 (permanent or !dad_failed) | void (in6_ifa_put(ifp)) | YES | YES (exactly one put) | ✅ Balanced | Single put releases the caller’s reference correctly. |
| L2145 (else: !temporary, !permanent, dad_failed) | void (ipv6_del_addr(ifp)) | YES | YES (via ipv6_del_addr) + **extra puts** (DAD work, interface‑list ref) | ❌ EXCESS PUT | **Warning line** – ipv6_del_addr drops more references than held (caller’s ref was the only one), causing refcount underflow. Should use in6_ifa_put instead. |

**Pre‑verdict checklist:**
- “Held for device lifetime”? Not applicable – no deferred release pattern.
- “Ownership transferred”? No – the caller holds the only reference to be released.
- Unconditional GET? The caller’s reference is unconditional; the bug is that the release path on L2145 calls `ipv6_del_addr` which internally performs `addrconf_del_dad_work`‑put + `in6_ifa_put` + `__in6_ifa_put`, while only a single `in6_ifa_put` is correct in this state.
- goto between GET and PUT? No goto, but the else branch chooses the wrong put function.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On line 2145, the else branch calls `ipv6_del_addr()` which internally drops multiple references (DAD work, interface list) not held by the caller, causing a refcount excess put (underflow). The correct call is `in6_ifa_put(ifp)`.
```
